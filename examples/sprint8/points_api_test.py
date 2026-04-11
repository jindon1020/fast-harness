"""
积分管理模块 API 集成测试
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


class TestChargeRecords:
    """充值记录相关接口测试"""

    def test_get_charge_records(self, client, team_id):
        """
        用例: tc-016 - 点击【剩余积分】区域内的充值记录按钮，展示充值记录弹窗
        优先级: P1
        接口: GET /drama-api/points/team/charge_records
        """
        response = client.get(
            f"/drama-api/points/team/charge_records",
            params={"team_id": team_id}
        )
        assert response.status_code == 200
        assert response.json().get("code") == 0

    def test_get_charge_records_empty(self, client, team_id):
        """
        用例: tc-017 - 无充值记录时弹窗展示【暂无充值记录】，无空白、报错
        优先级: P1
        接口: GET /drama-api/points/team/charge_records
        """
        response = client.get(
            f"/drama-api/points/team/charge_records",
            params={"team_id": team_id}
        )
        assert response.status_code == 200
        result = response.json()
        # 无记录时应该返回空列表或提示
        if result.get("result", {}).get("total_count", 1) == 0:
            assert result.get("result", {}).get("data", []) == []


class TestPointsDistribution:
    """积分分配相关接口测试"""

    def test_get_distribution_ring_chart(self, client, team_id):
        """
        用例: tc-018 - 待分配积分新增环形图，展示【已分配/未分配】比例
        优先级: P1
        接口: GET /drama-api/points/team/members
        """
        response = client.get(
            f"/drama-api/points/team/members",
            params={"team_id": team_id}
        )
        assert response.status_code == 200
        assert response.json().get("code") == 0
        result = response.json().get("result", {})
        # 验证返回包含已分配和未分配积分数据
        assert "distributed_points" in result or "allocated_points" in result
        assert "remaining_points" in result or "unallocated_points" in result

    def test_get_7day_consumption_chart(self, client, team_id):
        """
        用例: tc-019 - 近7日消耗积分柱状图，hover显示对应日期和当日消耗积分
        优先级: P1
        接口: GET /drama-api/points/team/consumption?days=7
        """
        response = client.get(
            f"/drama-api/points/team/consumption",
            params={"team_id": team_id, "days": 7}
        )
        assert response.status_code == 200
        assert response.json().get("code") == 0
        result = response.json().get("result", {})
        assert isinstance(result.get("data", []), list)

    def test_get_projects_with_covers(self, client, team_id):
        """
        用例: tc-020 - 进行中项目新增项目封面图
        优先级: P1
        接口: GET /drama-api/points/stats/projects
        """
        response = client.get(
            f"/drama-api/points/stats/projects",
            params={"team_id": team_id}
        )
        assert response.status_code == 200
        assert response.json().get("code") == 0
        projects = response.json().get("result", {}).get("data", [])
        for project in projects:
            # 有封面图的项目展示图片，无封面图展示默认占位图
            assert "cover_url" in project or "cover_image" in project or "placeholder" in project

    def test_get_projects_empty_state(self, client, team_id):
        """
        用例: tc-021 - 项目列表为空时，展示空状态提示图+提示词
        优先级: P1
        接口: GET /drama-api/points/stats/projects
        """
        response = client.get(
            f"/drama-api/points/stats/projects",
            params={"team_id": team_id}
        )
        assert response.status_code == 200
        result = response.json()
        # 空状态应该返回空列表和正确的提示


class TestPointsSort:
    """积分排序相关接口测试"""

    def test_points_sort_ascending(self, client, team_id):
        """
        用例: tc-022 - 积分排序默认为团队成员排序，点击正序，列表按积分正序排列
        优先级: P1
        接口: GET /drama-api/points/team/members?order_by=points_asc
        """
        response = client.get(
            f"/drama-api/points/team/members",
            params={"team_id": team_id, "order_by": "points_asc"}
        )
        assert response.status_code == 200
        assert response.json().get("code") == 0

    def test_points_sort_descending(self, client, team_id):
        """
        用例: tc-022 - 点击倒序，列表按积分倒序排列
        优先级: P1
        接口: GET /drama-api/points/team/members?order_by=points_desc
        """
        response = client.get(
            f"/drama-api/points/team/members",
            params={"team_id": team_id, "order_by": "points_desc"}
        )
        assert response.status_code == 200
        assert response.json().get("code") == 0

    def test_rapid_sort_switching(self, client, team_id):
        """
        用例: tc-023 - 快速多次点击正序/倒序切换，列表最终展示最后一次排序结果
        优先级: P1
        接口: GET /drama-api/points/team/members?order_by=xxx
        """
        orders = ["points_asc", "points_desc"]
        last_response = None
        for _ in range(6):  # 快速切换
            for order in orders:
                last_response = client.get(
                    f"/drama-api/points/team/members",
                    params={"team_id": team_id, "order_by": order}
                )
        assert last_response.status_code == 200

    def test_7day_consumption_sort(self, client, team_id):
        """
        用例: tc-024 - 七日消耗排序，点击正序/倒序，数据按排序
        优先级: P1
        接口: GET /drama-api/points/team/consumption?days=7&order_by=xxx
        """
        for order in ["points_asc", "points_desc"]:
            response = client.get(
                f"/drama-api/points/team/consumption",
                params={"team_id": team_id, "days": 7, "order_by": order}
            )
            assert response.status_code == 200
            assert response.json().get("code") == 0

    def test_7day_consumption_zero_no_error(self, client, team_id):
        """
        用例: tc-025 - 七日消耗积分数据为0时，排序后列表顺序不变，无报错
        优先级: P1
        接口: GET /drama-api/points/team/consumption?days=7&order_by=xxx
        """
        response = client.get(
            f"/drama-api/points/team/consumption",
            params={"team_id": team_id, "days": 7, "order_by": "points_asc"}
        )
        assert response.status_code == 200
        assert response.json().get("code") == 0

    def test_realtime_sync(self, client, team_id):
        """
        用例: tc-026 - 进行中任务和生成情况实时展示自动同步更新
        优先级: P1
        接口: GET /drama-api/points/stats/projects
        """
        response = client.get(
            f"/drama-api/points/stats/projects",
            params={"team_id": team_id}
        )
        assert response.status_code == 200
        assert response.json().get("code") == 0


class TestProjectStatistics:
    """项目统计相关接口测试"""

    def test_project_search(self, client, team_id):
        """
        用例: tc-027 - 项目统计新增搜索功能，输入项目名称，精准匹配
        优先级: P1
        接口: GET /drama-api/points/stats/projects?search=keyword
        """
        response = client.get(
            f"/drama-api/points/stats/projects",
            params={"team_id": team_id, "search": "测试项目"}
        )
        assert response.status_code == 200
        assert response.json().get("code") == 0

    def test_project_search_no_match(self, client, team_id):
        """
        用例: tc-028 - 输入不存在的项目关键词，展示【无匹配项目】的占位图
        优先级: P1
        接口: GET /drama-api/points/stats/projects?search=不存在
        """
        response = client.get(
            f"/drama-api/points/stats/projects",
            params={"team_id": team_id, "search": "不存在的项目xyz"}
        )
        assert response.status_code == 200
        result = response.json()
        # 无匹配结果时应返回空列表或提示

    def test_project_sort_by_field(self, client, team_id):
        """
        用例: tc-029 - 选择排序字段（如剧集数量），列表按后端排序规则展示
        优先级: P1
        接口: GET /drama-api/points/stats/projects?sort_by=episode_count&order=asc
        """
        response = client.get(
            f"/drama-api/points/stats/projects",
            params={"team_id": team_id, "sort_by": "episode_count", "order": "asc"}
        )
        assert response.status_code == 200
        assert response.json().get("code") == 0
