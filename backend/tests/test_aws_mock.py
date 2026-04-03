"""Tests for AWS Mock Service."""

import pytest
import asyncio
from app.services.aws_mock.service import AWSMockService


@pytest.fixture
def aws():
    svc = AWSMockService()
    svc.reset_state()
    return svc


def test_load_state(aws):
    state = aws.get_full_state()
    assert "security_groups" in state
    assert "s3_buckets" in state
    assert "iam_policies" in state
    assert "sg-0a1b2c3d4e5f6g7h8" in state["security_groups"]


def test_describe_security_groups(aws):
    result = asyncio.run(aws.describe_security_groups("sg-0a1b2c3d4e5f6g7h8"))
    assert "SecurityGroups" in result
    sg = result["SecurityGroups"][0]
    assert sg["name"] == "web-server-sg"
    assert len(sg["ingress_rules"]) == 3  # 443, 80, 22


def test_revoke_ingress(aws):
    result = asyncio.run(
        aws.revoke_security_group_ingress(
            "sg-0a1b2c3d4e5f6g7h8", "sgr-ingress-22"
        )
    )
    assert result["Return"] is True

    # Verify rule was removed
    sg = asyncio.run(aws.describe_security_groups("sg-0a1b2c3d4e5f6g7h8"))
    rules = sg["SecurityGroups"][0]["ingress_rules"]
    assert len(rules) == 2  # Only 443 and 80 remain
    assert all(r["rule_id"] != "sgr-ingress-22" for r in rules)


def test_put_public_access_block(aws):
    result = asyncio.run(aws.put_public_access_block("aegis-company-data-2026"))
    assert "RequestId" in result

    # Verify bucket is now private
    block = asyncio.run(aws.get_public_access_block("aegis-company-data-2026"))
    config = block["PublicAccessBlockConfiguration"]
    assert config["block_public_acls"] is True
    assert config["restrict_public_buckets"] is True


def test_generate_diff_port22(aws):
    diff = aws.generate_diff("open-port-22")
    assert diff["resource_type"] == "security-group"
    assert diff["before"]["status"] == "OPEN"
    assert diff["after"]["status"] == "CLOSED"
    assert "\U0001f534" in diff["before"]["display"]  # Red circle
    assert "\U0001f7e2" in diff["after"]["display"]    # Green circle


def test_reset_state(aws):
    asyncio.run(aws.revoke_security_group_ingress(
        "sg-0a1b2c3d4e5f6g7h8", "sgr-ingress-22"
    ))
    aws.reset_state()
    sg = asyncio.run(aws.describe_security_groups("sg-0a1b2c3d4e5f6g7h8"))
    assert len(sg["SecurityGroups"][0]["ingress_rules"]) == 3  # Back to original
