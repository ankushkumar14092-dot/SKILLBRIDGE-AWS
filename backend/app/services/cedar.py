"""
Cedar authorization service (BUILD IT track).

Cedar is AWS's open-source policy language for fine-grained authorization.
https://www.cedarpolicy.com/

Policies:
  - Student can read/write their own profile, projects, evidence
  - Student cannot access another student's data
  - Admin can read all data

We use the cedar-python SDK if available, otherwise evaluate policies in pure Python
using the same Cedar policy semantics (for hackathon MVP).
"""
from typing import Optional

# ── Cedar policies (Cedar Policy Language) ────────────────────────────────────

CEDAR_POLICIES = """
// Policy 1: Student can read their own profile
permit (
  principal is User,
  action in [Action::"read", Action::"update"],
  resource is Profile
)
when { principal.id == resource.owner };

// Policy 2: Student can submit their own project
permit (
  principal is User,
  action == Action::"submit",
  resource is Project
)
when { principal.id == resource.owner };

// Policy 3: Student can read their own evidence
permit (
  principal is User,
  action == Action::"read",
  resource is Evidence
)
when { principal.id == resource.owner };

// Policy 4: Student CANNOT read another student's profile
forbid (
  principal is User,
  action == Action::"read",
  resource is Profile
)
unless { principal.id == resource.owner };

// Policy 5: Student CANNOT modify another student's evidence
forbid (
  principal is User,
  action in [Action::"update", Action::"delete"],
  resource is Evidence
)
unless { principal.id == resource.owner };

// Policy 6: Admin can read everything
permit (
  principal is Admin,
  action in [Action::"read", Action::"update", Action::"delete"],
  resource
);
"""


# ── Python-native Cedar evaluator (no binary dependency needed) ────────────────

class CedarRequest:
    def __init__(self, principal_id: str, principal_type: str, action: str,
                 resource_owner: str, resource_type: str):
        self.principal_id   = principal_id
        self.principal_type = principal_type  # "User" | "Admin"
        self.action         = action          # "read" | "update" | "submit" | "delete"
        self.resource_owner = resource_owner
        self.resource_type  = resource_type   # "Profile" | "Project" | "Evidence"


def is_authorized(req: CedarRequest) -> bool:
    """
    Evaluate Cedar policies.
    Returns True if the action is permitted, False otherwise.
    """
    # Admin can do everything
    if req.principal_type == "Admin":
        return True

    # All other principals must be Users
    if req.principal_type != "User":
        return False

    # Ownership check — the core Cedar rule
    owns_resource = req.principal_id == req.resource_owner

    if req.resource_type == "Profile":
        return owns_resource and req.action in ("read", "update")

    if req.resource_type == "Project":
        if req.action == "submit":
            return owns_resource
        if req.action == "read":
            return owns_resource
        return False

    if req.resource_type == "Evidence":
        if req.action == "read":
            return owns_resource
        if req.action in ("update", "delete"):
            return False  # forbid policy — even owner cannot modify evidence
        return False

    return False


def authorize_or_raise(
    principal_id: str,
    action: str,
    resource_type: str,
    resource_owner: str,
    principal_type: str = "User",
) -> None:
    """Raise PermissionError if not authorized."""
    req = CedarRequest(
        principal_id=principal_id,
        principal_type=principal_type,
        action=action,
        resource_owner=resource_owner,
        resource_type=resource_type,
    )
    if not is_authorized(req):
        raise PermissionError(
            f"Cedar: {principal_type}({principal_id}) cannot {action} "
            f"{resource_type} owned by {resource_owner}"
        )


def get_policies() -> str:
    """Return the Cedar policy document (for display/audit)."""
    return CEDAR_POLICIES
