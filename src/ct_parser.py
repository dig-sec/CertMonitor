import base64
import hashlib
import time
from datetime import datetime, timezone
from typing import Optional
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.x509.oid import NameOID, ExtensionOID
from cryptography.hazmat.primitives.asymmetric import rsa, ec

def calculate_valid_days(not_before: datetime, not_after: datetime) -> int:
    return (not_after - not_before).days


def get_key_usage(cert: x509.Certificate) -> list:
    try:
        ku = cert.extensions.get_extension_for_oid(ExtensionOID.KEY_USAGE).value
        usage = []
        for attr in [
            ('digital_signature', ku.digital_signature),
            ('content_commitment', ku.content_commitment),
            ('key_encipherment', ku.key_encipherment),
            ('data_encipherment', ku.data_encipherment),
            ('key_agreement', ku.key_agreement),
            ('key_cert_sign', ku.key_cert_sign),
            ('crl_sign', ku.crl_sign),
        ]:
            if attr[1]:
                usage.append(attr[0])
        return usage
    except x509.ExtensionNotFound:
        return []


def get_extended_key_usage(cert: x509.Certificate) -> list:
    try:
        eku = cert.extensions.get_extension_for_oid(ExtensionOID.EXTENDED_KEY_USAGE).value
        return [usage._name.lower() for usage in eku]
    except x509.ExtensionNotFound:
        return []


def get_domains_from_cert(cert: x509.Certificate) -> list:
    domains = []
    try:
        for attr in cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME):
            if attr.value not in domains:
                domains.append(attr.value)
    except Exception:
        pass
    try:
        san = cert.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_ALTERNATIVE_NAME).value
        for name in san.get_values_for_type(x509.DNSName):
            if name not in domains:
                domains.append(name)
    except x509.ExtensionNotFound:
        pass
    return domains


def get_issuer_name(cert: x509.Certificate) -> str:
    name = None
    try:
        issuer_cn = cert.issuer.get_attributes_for_oid(NameOID.COMMON_NAME)
        if issuer_cn:
            name = issuer_cn[0].value
    except Exception:
        pass
    if not name:
        try:
            issuer_o = cert.issuer.get_attributes_for_oid(NameOID.ORGANIZATION_NAME)
            if issuer_o:
                name = issuer_o[0].value
        except Exception:
            pass
    if not name:
        name = cert.issuer.rfc4514_string()
    return name


def parse_ct_entry(entry: dict, log_url: str, index: int, seen_certs: dict, seen_lock) -> Optional[dict]:
    leaf_b64 = entry.get("leaf_input")
    extra_b64 = entry.get("extra_data")
    if not leaf_b64 or not extra_b64:
        return None
    
    try:
        leaf_bytes = base64.b64decode(leaf_b64)
        extra_bytes = base64.b64decode(extra_b64)
    except Exception as e:
        logging.warning(f"Base64 decoding error: {e}")
        return None
    
    if len(leaf_bytes) < 12:
        return None
    
    entry_type = int.from_bytes(leaf_bytes[10:12], byteorder='big')
    leaf_cert_bytes = None
    chain_cert_bytes = []
    
    try:
        if entry_type == 0:  # X509LogEntry
            if len(leaf_bytes) < 15:
                return None
            cert_len = int.from_bytes(leaf_bytes[12:15], byteorder='big')
            leaf_cert_bytes = leaf_bytes[15:15+cert_len]
            offset = 0
            while offset < len(extra_bytes):
                if offset + 3 > len(extra_bytes):
                    break
                cert_len = int.from_bytes(extra_bytes[offset:offset+3], byteorder='big')
                offset += 3
                if offset + cert_len > len(extra_bytes):
                    break
                cert_bytes = extra_bytes[offset:offset+cert_len]
                offset += cert_len
                if cert_bytes:
                    chain_cert_bytes.append(cert_bytes)
        elif entry_type == 1:  # PrecertLogEntry
            offset = 0
            if len(extra_bytes) < 3:
                return None
            precert_len = int.from_bytes(extra_bytes[offset:offset+3], byteorder='big')
            offset += 3
            if offset + precert_len > len(extra_bytes):
                return None
            leaf_cert_bytes = extra_bytes[offset:offset+precert_len]
            offset += precert_len
            while offset < len(extra_bytes):
                if offset + 3 > len(extra_bytes):
                    break
                cert_len = int.from_bytes(extra_bytes[offset:offset+3], byteorder='big')
                offset += 3
                if offset + cert_len > len(extra_bytes):
                    break
                cert_bytes = extra_bytes[offset:offset+cert_len]
                offset += cert_len
                if cert_bytes:
                    chain_cert_bytes.append(cert_bytes)
        else:
            return None
    except Exception as e:
        logging.error(f"Error parsing entry structure: {e}")
        return None
    
    try:
        cert = x509.load_der_x509_certificate(leaf_cert_bytes, default_backend())
    except Exception as e:
        logging.error(f"Certificate parse error: {e}")
        return None

    fingerprint = hashlib.sha256(leaf_cert_bytes).hexdigest().upper()
    with seen_lock:
        if fingerprint in seen_certs:
            return None
        seen_certs[fingerprint] = True

    not_before = cert.not_valid_before_utc.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
    not_after = cert.not_valid_after_utc.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
    current_time = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
    
    chain_summary = []
    for cbytes in chain_cert_bytes:
        try:
            chain_cert = x509.load_der_x509_certificate(cbytes, default_backend())
            cn = chain_cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
            chain_summary.append({
                "cn": cn[0].value if cn else chain_cert.subject.rfc4514_string(),
                "not_after": chain_cert.not_valid_after_utc.isoformat(timespec='milliseconds') + "Z"
            })
        except Exception:
            continue

    try:
        aia = cert.extensions.get_extension_for_oid(ExtensionOID.AUTHORITY_INFORMATION_ACCESS).value
        ocsp_urls = [ad.access_location.value for ad in aia if ad.access_method == x509.oid.AuthorityInformationAccessOID.OCSP]
        issuer_urls = [ad.access_location.value for ad in aia if ad.access_method == x509.oid.AuthorityInformationAccessOID.CA_ISSUERS]
        ocsp_url = ocsp_urls[0] if ocsp_urls else None
        issuer_cert_url = issuer_urls[0] if issuer_urls else None
    except x509.ExtensionNotFound:
        ocsp_url = None
        issuer_cert_url = None

    try:
        crl_dps = cert.extensions.get_extension_for_oid(ExtensionOID.CRL_DISTRIBUTION_POINTS).value
        crl_urls = [dp.full_name[0].value for dp in crl_dps if dp.full_name]
        crl_url = crl_urls[0] if crl_urls else None
    except x509.ExtensionNotFound:
        crl_url = None

    # Handle different public key types
    public_key = cert.public_key()
    if isinstance(public_key, rsa.RSAPublicKey):
        algorithm = "rsa"
        key_size = public_key.key_size
        public_exponent = public_key.public_numbers().e
        curve_name = None
    elif isinstance(public_key, ec.EllipticCurvePublicKey):
        algorithm = "ec"
        key_size = public_key.key_size
        public_exponent = None
        curve_name = public_key.curve.name
    else:
        algorithm = "unknown"
        key_size = None
        public_exponent = None
        curve_name = None

    return {
        "log_url": log_url,
        "timestamp": int(time.time() * 1000),
        "type": "x509",
        "update_type": "X509LogEntry" if entry_type == 0 else "PrecertLogEntry",
        "fingerprint": fingerprint,
        "version": cert.version.value + 1,
        "serial_number": str(cert.serial_number),
        "signature_algorithm": f"{cert.signature_hash_algorithm.name}_{algorithm}",
        "issuer_cn": get_issuer_name(cert),
        "subject_cn": cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value if cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME) else None,
        "validity": {
            "not_before": not_before,
            "not_after": not_after,
            "valid_days": calculate_valid_days(cert.not_valid_before_utc, cert.not_valid_after_utc)
        },
        "subject_public_key_info": {
            "algorithm": algorithm,
            "key_size_bits": key_size,
            "public_exponent": public_exponent,
            "curve_name": curve_name
        },
        "all_domains": get_domains_from_cert(cert),
        "ocsp_url": ocsp_url,
        "issuer_cert_url": issuer_cert_url,
        "crl_url": crl_url,
        "key_usage": get_key_usage(cert),
        "extended_key_usage": get_extended_key_usage(cert),
        "cert_index": index,
        "cert_link": f"{log_url}ct/v1/get-entries?start={index}&end={index}",
        "@timestamp": current_time,
        "seen": current_time,
        "source": {
            "url": log_url,
            "name": ""
        },
        "chain_summary": chain_summary
    }