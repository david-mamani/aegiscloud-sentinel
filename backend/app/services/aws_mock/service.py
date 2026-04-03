"""
AWS Mock Service — Simulates AWS API responses.

This module provides a complete simulation of AWS API calls
for the hackathon. In production, this would be replaced by
boto3 with real credentials from Auth0 Token Vault.

IMPORTANT: State is mutable in-memory to demonstrate before/after diffs.
"""

import json
import uuid
import copy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"


class AWSMockService:
    """
    Simulates AWS EC2, S3, and IAM API responses.

    All operations modify in-memory state to demonstrate
    the remediation effect in the dashboard diff viewer.
    """

    def __init__(self):
        self._initial_state: dict = {}
        self._current_state: dict = {}
        self._action_log: list[dict] = []
        self._load_initial_state()

    def _load_initial_state(self):
        """Load infrastructure state from JSON file."""
        state_file = DATA_DIR / "infrastructure_state.json"
        with open(state_file, "r") as f:
            self._initial_state = json.load(f)
        self._current_state = copy.deepcopy(self._initial_state)

    def reset_state(self):
        """Reset to initial vulnerable state (for demo reruns)."""
        self._current_state = copy.deepcopy(self._initial_state)
        self._action_log.clear()

    def get_full_state(self) -> dict:
        """Return complete current infrastructure state."""
        return copy.deepcopy(self._current_state)

    def get_action_log(self) -> list[dict]:
        """Return log of all actions performed."""
        return copy.deepcopy(self._action_log)

    def get_vulnerabilities(self) -> list[dict]:
        """Return a flat list of all current non-compliant findings."""
        vulns = []
        state = self._current_state

        # Check security groups
        for sg_id, sg in state.get("security_groups", {}).items():
            for rule in sg.get("ingress_rules", []):
                if not rule.get("compliant", True):
                    vulns.append({
                        "resource_type": "security-group",
                        "resource_id": sg_id,
                        "resource_name": sg.get("name"),
                        "rule_id": rule["rule_id"],
                        "severity": rule.get("severity", "UNKNOWN"),
                        "risk_score": rule.get("risk_score", 0),
                        "cis_benchmark": rule.get("cis_benchmark", ""),
                        "description": rule.get("description", ""),
                    })

        # Check S3 buckets
        for bucket_name, bucket in state.get("s3_buckets", {}).items():
            if not bucket.get("compliant", True):
                vulns.append({
                    "resource_type": "s3-bucket",
                    "resource_id": bucket_name,
                    "resource_name": bucket_name,
                    "severity": bucket.get("severity", "UNKNOWN"),
                    "risk_score": bucket.get("risk_score", 0),
                    "cis_benchmark": bucket.get("cis_benchmark", ""),
                    "description": f"Bucket {bucket_name} has public access enabled",
                })

        # Check IAM policies
        for policy_id, policy in state.get("iam_policies", {}).items():
            if not policy.get("compliant", True):
                vulns.append({
                    "resource_type": "iam-policy",
                    "resource_id": policy_id,
                    "resource_name": policy.get("name"),
                    "severity": policy.get("severity", "UNKNOWN"),
                    "risk_score": policy.get("risk_score", 0),
                    "cis_benchmark": policy.get("cis_benchmark", ""),
                    "description": policy.get("description", ""),
                })

        # Sort by risk score descending
        vulns.sort(key=lambda v: v.get("risk_score", 0), reverse=True)
        return vulns

    # --- EC2: Security Groups ---

    async def describe_security_groups(
        self, group_id: str | None = None
    ) -> dict:
        """Simulate ec2:DescribeSecurityGroups."""
        sgs = self._current_state.get("security_groups", {})

        if group_id:
            sg = sgs.get(group_id)
            if not sg:
                return {"error": "SecurityGroupNotFound", "group_id": group_id}
            return {
                "SecurityGroups": [sg],
                "RequestId": str(uuid.uuid4()),
            }

        return {
            "SecurityGroups": list(sgs.values()),
            "RequestId": str(uuid.uuid4()),
        }

    async def revoke_security_group_ingress(
        self, group_id: str, rule_id: str, token: str = "mock-token"
    ) -> dict:
        """
        Simulate ec2:RevokeSecurityGroupIngress.

        Removes a specific ingress rule from a security group.
        Requires a valid token (from Token Vault in production).
        """
        sgs = self._current_state.get("security_groups", {})
        sg = sgs.get(group_id)

        if not sg:
            return {"error": "SecurityGroupNotFound", "group_id": group_id}

        original_count = len(sg["ingress_rules"])
        sg["ingress_rules"] = [
            r for r in sg["ingress_rules"] if r["rule_id"] != rule_id
        ]

        removed = original_count > len(sg["ingress_rules"])

        action = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": "ec2",
            "action": "RevokeSecurityGroupIngress",
            "resource": group_id,
            "rule_id": rule_id,
            "success": removed,
            "token_used": token[:20] + "..." if len(token) > 20 else token,
            "request_id": str(uuid.uuid4()),
        }
        self._action_log.append(action)

        return {
            "Return": removed,
            "RequestId": action["request_id"],
            "action_log": action,
        }

    # --- S3: Bucket Operations ---

    async def get_public_access_block(self, bucket_name: str) -> dict:
        """Simulate s3:GetPublicAccessBlock."""
        buckets = self._current_state.get("s3_buckets", {})
        bucket = buckets.get(bucket_name)

        if not bucket:
            return {"error": "NoSuchBucket", "bucket": bucket_name}

        return {
            "PublicAccessBlockConfiguration": bucket["public_access_block"],
            "RequestId": str(uuid.uuid4()),
        }

    async def put_public_access_block(
        self, bucket_name: str, token: str = "mock-token"
    ) -> dict:
        """
        Simulate s3:PutPublicAccessBlock.

        Enables all public access block settings on a bucket.
        """
        buckets = self._current_state.get("s3_buckets", {})
        bucket = buckets.get(bucket_name)

        if not bucket:
            return {"error": "NoSuchBucket", "bucket": bucket_name}

        bucket["public_access_block"] = {
            "block_public_acls": True,
            "ignore_public_acls": True,
            "block_public_policy": True,
            "restrict_public_buckets": True,
        }
        bucket["bucket_policy_public"] = False
        bucket["compliant"] = True
        bucket["severity"] = "NONE"
        bucket["risk_score"] = 0.0

        action = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": "s3",
            "action": "PutPublicAccessBlock",
            "resource": bucket_name,
            "success": True,
            "token_used": token[:20] + "..." if len(token) > 20 else token,
            "request_id": str(uuid.uuid4()),
        }
        self._action_log.append(action)

        return {
            "RequestId": action["request_id"],
            "action_log": action,
        }

    # --- Diff Generation ---

    def generate_diff(self, scenario_id: str) -> dict:
        """
        Generate a before/after diff for a remediation scenario.

        This diff is used in the RAR payload sent to Auth0 Guardian
        so the human approver can see exactly what will change.
        """
        scenarios_file = DATA_DIR / "scenarios.json"
        with open(scenarios_file, "r") as f:
            scenarios = json.load(f)["scenarios"]

        scenario = next(
            (s for s in scenarios if s["id"] == scenario_id), None
        )
        if not scenario:
            return {"error": f"Scenario {scenario_id} not found"}

        if scenario_id == "open-port-22":
            return self._diff_security_group_rule(
                "sg-0a1b2c3d4e5f6g7h8", "sgr-ingress-22"
            )
        elif scenario_id == "public-s3":
            return self._diff_s3_public_access("aegis-company-data-2026")
        elif scenario_id == "db-exposed":
            return self._diff_security_group_rule(
                "sg-9i8h7g6f5e4d3c2b1", "sgr-ingress-3306-public"
            )
        elif scenario_id == "iam-overpriv":
            return self._diff_iam_policy("policy-admin-wildcard")

        return {"error": "Diff not implemented for this scenario"}

    def _diff_security_group_rule(
        self, group_id: str, rule_id: str
    ) -> dict:
        """Generate diff for removing a security group rule."""
        sg = self._current_state["security_groups"].get(group_id, {})
        rule = next(
            (r for r in sg.get("ingress_rules", []) if r["rule_id"] == rule_id),
            None,
        )

        if not rule:
            return {"error": "Rule not found or already remediated"}

        return {
            "resource_type": "security-group",
            "resource_id": group_id,
            "resource_name": sg.get("name", "unknown"),
            "change_type": "REMOVE_RULE",
            "before": {
                "rule_id": rule["rule_id"],
                "protocol": rule["protocol"],
                "port_range": f"{rule['from_port']}-{rule['to_port']}",
                "source": rule["source"],
                "status": "OPEN",
                "severity": rule.get("severity", "UNKNOWN"),
                "display": f"\U0001f534 Port {rule['from_port']} ({rule['protocol'].upper()}) \u2014 OPEN to {rule['source']}",
            },
            "after": {
                "rule_id": rule["rule_id"],
                "protocol": rule["protocol"],
                "port_range": f"{rule['from_port']}-{rule['to_port']}",
                "source": "REMOVED",
                "status": "CLOSED",
                "severity": "NONE",
                "display": f"\U0001f7e2 Port {rule['from_port']} ({rule['protocol'].upper()}) \u2014 CLOSED (rule removed)",
            },
        }

    def _diff_s3_public_access(self, bucket_name: str) -> dict:
        """Generate diff for enabling S3 public access block."""
        bucket = self._current_state["s3_buckets"].get(bucket_name, {})

        return {
            "resource_type": "s3-bucket",
            "resource_id": bucket_name,
            "resource_name": bucket_name,
            "change_type": "ENABLE_PUBLIC_ACCESS_BLOCK",
            "before": {
                "block_public_acls": False,
                "ignore_public_acls": False,
                "block_public_policy": False,
                "restrict_public_buckets": False,
                "status": "PUBLIC",
                "display": "\U0001f534 Bucket PUBLIC \u2014 All public access block settings DISABLED",
            },
            "after": {
                "block_public_acls": True,
                "ignore_public_acls": True,
                "block_public_policy": True,
                "restrict_public_buckets": True,
                "status": "PRIVATE",
                "display": "\U0001f7e2 Bucket PRIVATE \u2014 All public access block settings ENABLED",
            },
        }

    def _diff_iam_policy(self, policy_id: str) -> dict:
        """Generate diff for restricting an overprivileged IAM policy."""
        policy = self._current_state["iam_policies"].get(policy_id, {})

        return {
            "resource_type": "iam-policy",
            "resource_id": policy_id,
            "resource_name": policy.get("name", "unknown"),
            "change_type": "RESTRICT_POLICY",
            "before": {
                "effect": "Allow",
                "action": "*",
                "resource": "*",
                "status": "OVERPRIVILEGED",
                "display": "\U0001f534 IAM Policy grants * (ALL) actions on * (ALL) resources",
            },
            "after": {
                "effect": "Allow",
                "action": ["lambda:InvokeFunction", "logs:CreateLogGroup", "logs:PutLogEvents"],
                "resource": "arn:aws:lambda:us-east-1:123456789012:function:*",
                "status": "LEAST_PRIVILEGE",
                "display": "\U0001f7e2 IAM Policy scoped to lambda:Invoke + logs only",
            },
        }


# Singleton instance
aws_mock = AWSMockService()
