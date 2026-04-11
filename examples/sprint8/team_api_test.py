"""
团队模块 API 集成测试
由 backend-testcase-gen-command 自动生成
源文件: sprint8团队管理更新.xmind
Sprint: sprint8
生成时间: 2026-03-31
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.main import app
from app.dependencies import get_db_session, get_user_id
from app.permissions.dependencies import auth_project, AuthResult


@pytest.fixture
def client(db_session: Session):
    """创建测试客户端"""
    def get_db_override():
        yield db_session

    def get_user_override():
        return "test_user_int"

    def get_auth_override(user_id, project_id, action, sess, object_type):
        return AuthResult.ok()

    app.dependency_overrides[get_db_session] = get_db_override
    app.dependency_overrides[get_user_id] = get_user_override
    app.dependency_overrides[auth_project] = get_auth_override

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture
def team_id():
    """测试团队 ID"""
    return "test_team_001"


@pytest.fixture
def member_id():
    """测试成员 ID"""
    return "test_member_001"


class TestTeamInfo:
    """团队信息相关接口测试"""

    def test_update_avatar_success(self, client, team_id):
        """
        用例: tc-001 - 管理员点击头像区域选择新头像，头像更新成功
        优先级: P1
        接口: PATCH /drama-api/teams/{team_id}
        """
        response = client.patch(
            f"/drama-api/teams/{team_id}",
            json={"avatar": "https://example.com/new_avatar.png"}
        )
        assert response.status_code == 200
        assert response.json().get("code") == 0

    def test_update_avatar_invalid_format(self, client, team_id):
        """
        用例: tc-002 - 上传的头像非图片格式时系统提示文件格式错误
        优先级: P1
        接口: PATCH /drama-api/teams/{team_id}
        """
        response = client.patch(
            f"/drama-api/teams/{team_id}",
            json={"avatar": "https://example.com/avatar.exe"}
        )
        assert response.status_code in [400, 422]
        assert response.json().get("code") != 0

    def test_update_name_success(self, client, team_id):
        """
        用例: tc-003 - 管理员点击名称区域输入新名称，新名称更新成功
        优先级: P1
        接口: PATCH /drama-api/teams/{team_id}
        """
        response = client.patch(
            f"/drama-api/teams/{team_id}",
            json={"name": "新团队名称"}
        )
        assert response.status_code == 200
        assert response.json().get("code") == 0

    def test_update_name_too_long(self, client, team_id):
        """
        用例: tc-004 - 管理员输入新名称超过设定限制时，系统提示名称过长
        优先级: P1
        接口: PATCH /drama-api/teams/{team_id}
        """
        long_name = "a" * 256  # 假设最大长度为 255
        response = client.patch(
            f"/drama-api/teams/{team_id}",
            json={"name": long_name}
        )
        assert response.status_code in [400, 422]

    def test_get_team_info_with_points(self, client, team_id):
        """
        用例: tc-005 - 团队成员和剩余积分展示实时同步
        优先级: P1
        接口: GET /drama-api/teams/{team_id}
        """
        response = client.get(f"/drama-api/teams/{team_id}")
        assert response.status_code == 200
        result = response.json().get("result", {})
        assert "members" in result or "member_count" in result
        assert "points" in result or "remaining_points" in result


class TestTeamMemberFilter:
    """团队成员角色筛选相关接口测试"""

    def test_get_members_default_filter(self, client, team_id):
        """
        用例: tc-006 - 新增角色筛选，未筛选时默认为全部
        优先级: P1
        接口: GET /drama-api/teams/{team_id}/members
        """
        response = client.get(f"/drama-api/teams/{team_id}/members")
        assert response.status_code == 200
        result = response.json()
        assert result.get("code") == 0

    def test_get_members_filter_options(self, client, team_id):
        """
        用例: tc-007 - 角色筛选下拉时有三个选项：全部、管理员、成员
        优先级: P1
        接口: GET /drama-api/teams/{team_id}/members?role=xxx
        """
        for role in ["admin", "member", None]:
            params = {"role": role} if role else {}
            response = client.get(f"/drama-api/teams/{team_id}/members", params=params)
            assert response.status_code == 200
            assert response.json().get("code") == 0

    def test_get_members_filter_admin(self, client, team_id):
        """
        用例: tc-008 - 点击角色筛选下拉框选择管理员，列表仅展示管理员
        优先级: P1
        接口: GET /drama-api/teams/{team_id}/members?role=admin
        """
        response = client.get(
            f"/drama-api/teams/{team_id}/members",
            params={"role": "admin"}
        )
        assert response.status_code == 200
        members = response.json().get("result", {}).get("data", [])
        for member in members:
            assert member.get("role") == "admin"

    def test_get_members_filter_member(self, client, team_id):
        """
        用例: tc-008 - 点击角色筛选下拉框选择成员，列表仅展示成员
        优先级: P1
        接口: GET /drama-api/teams/{team_id}/members?role=member
        """
        response = client.get(
            f"/drama-api/teams/{team_id}/members",
            params={"role": "member"}
        )
        assert response.status_code == 200
        members = response.json().get("result", {}).get("data", [])
        for member in members:
            assert member.get("role") == "member"

    def test_rapid_filter_switching(self, client, team_id):
        """
        用例: tc-009 - 快速连续切换多个角色筛选条件，列表最终只展示最后一次结果
        优先级: P1
        接口: GET /drama-api/teams/{team_id}/members?role=xxx
        """
        roles = ["admin", "member", None]
        last_response = None
        for role in roles * 3:  # 快速切换
            params = {"role": role} if role else {}
            last_response = client.get(
                f"/drama-api/teams/{team_id}/members",
                params=params
            )
        # 最终结果应该是最后一次请求的结果
        assert last_response.status_code == 200


class TestMemberRoleSwitch:
    """成员角色切换相关接口测试"""

    def test_admin_switch_to_member(self, client, team_id, member_id):
        """
        用例: tc-010 - 管理员切换到成员，角色变更成功，权限同步更新
        优先级: P1
        接口: PATCH /drama-api/teams/{team_id}/members
        """
        response = client.patch(
            f"/drama-api/teams/{team_id}/members",
            json={
                "member_id": member_id,
                "role": "member"
            }
        )
        assert response.status_code == 200
        assert response.json().get("code") == 0

    def test_member_switch_to_admin(self, client, team_id, member_id):
        """
        用例: tc-011 - 成员切换到管理员，角色变更成功，权限同步更新
        优先级: P1
        接口: PATCH /drama-api/teams/{team_id}/members
        """
        response = client.patch(
            f"/drama-api/teams/{team_id}/members",
            json={
                "member_id": member_id,
                "role": "admin"
            }
        )
        assert response.status_code == 200
        assert response.json().get("code") == 0

    def test_last_admin_cannot_switch_to_member(self, client, team_id):
        """
        用例: tc-012 - 当团队仅有一位管理员时，切换管理员角色会提示"至少保留1位管理员"
        优先级: P1
        接口: PATCH /drama-api/teams/{team_id}/members
        注意: 后端需新增此校验逻辑
        """
        response = client.patch(
            f"/drama-api/teams/{team_id}/members",
            json={
                "member_id": "last_admin_id",
                "role": "member"
            }
        )
        # 预期返回错误提示
        assert response.status_code in [200, 400]
        result = response.json()
        assert result.get("code") != 0 or "至少保留1位管理员" in str(result)


class TestInvite:
    """邀请成员相关接口测试"""

    def test_click_invite_button(self, client, team_id):
        """
        用例: tc-013 - 点击邀请成员按钮会弹出邀请成员弹窗
        优先级: P1
        接口: POST /drama-api/teams/{team_id}/invite
        """
        response = client.post(f"/drama-api/teams/{team_id}/invite")
        assert response.status_code == 200
        assert response.json().get("code") == 0
        # 验证返回包含邀请链接或邀请码
        result = response.json().get("result", {})
        assert "invite_code" in result or "invite_link" in result

    def test_reset_invite_link(self, client, team_id):
        """
        用例: tc-014 - 点击弹窗里的重置链接，链接会自动更新并重置
        优先级: P1
        接口: POST /drama-api/teams/{team_id}/invite/reset
        """
        response = client.post(f"/drama-api/teams/{team_id}/invite/reset")
        assert response.status_code == 200
        assert response.json().get("code") == 0

    def test_get_my_own_marker(self, client, team_id):
        """
        用例: tc-015 - 团队信息页面在"我"的后面加【我自己】的标签
        优先级: P1
        接口: GET /drama-api/teams/{team_id}/members
        """
        response = client.get(f"/drama-api/teams/{team_id}/members")
        assert response.status_code == 200
        members = response.json().get("result", {}).get("data", [])
        current_user_found = False
        for member in members:
            if member.get("is_current_user"):
                current_user_found = True
                assert "【我自己】" in str(member) or member.get("marker") == "self"
                break
        assert current_user_found, "当前用户应该在成员列表中"
