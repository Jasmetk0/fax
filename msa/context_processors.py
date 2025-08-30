from typing import Dict


def msa_admin_mode(request) -> Dict[str, bool]:
    return {"msa_admin_mode": bool(request.session.get("msa_admin"))}
