"""测试 ReportPreview 用 Kivy widget 渲染 ReportData。"""
from __future__ import annotations

from kivy.uix.label import Label

from app.ui.components.report_preview import ReportPreview


def _all_label_texts(widget: object) -> list[str]:
    """递归收集 widget 树中所有 Label 的文本。"""
    texts: list[str] = []
    if isinstance(widget, Label):
        texts.append(widget.text)
    for child in getattr(widget, "children", []):
        texts.extend(_all_label_texts(child))
    return texts


def _find_widgets(widget: object, cls: type) -> list:
    out: list = []
    if isinstance(widget, cls):
        out.append(widget)
    for child in getattr(widget, "children", []):
        out.extend(_find_widgets(child, cls))
    return out


class TestReportPreviewRender:
    """测试 ReportPreview 的 Kivy widget 渲染路径。"""

    def test_report_preview_without_data_shows_placeholder(self):
        """当 report_data 和 image_path 都为空时, 显示占位文字。"""
        preview = ReportPreview(image_path="", report_data=None, date_str="2026-06-07")
        content_box = preview._content_box
        assert len(content_box.children) > 0, (
            f"content_box 应该有至少一个子 widget, 实际 {len(content_box.children)}"
        )

    def test_report_preview_renders_report_data(self):
        """当提供 report_data 时, 渲染 Kivy widget 而非空白。"""
        from app.models.report import PeriodDetail, ReportData

        data = ReportData(
            date="2026-06-07",
            is_shooting_day=True,
            periods=[
                PeriodDetail(
                    period="morning",
                    checkin_time="09:00",
                    checkout_time="12:00",
                    status="normal",
                    status_label="正常",
                ),
                PeriodDetail(
                    period="afternoon",
                    checkin_time="14:00",
                    checkout_time="18:00",
                    status="normal",
                    status_label="正常",
                ),
            ],
            penalty_total=0.0,
            reward_total=10.0,
            net_amount=10.0,
            total_work_hours=7.0,
            overtime_hours=0.0,
            encouragement="继续加油!",
        )
        preview = ReportPreview(
            image_path="",
            report_data=data,
            date_str="2026-06-07",
        )
        content_box = preview._content_box
        assert len(content_box.children) > 0, (
            f"content_box 应该有至少一个子 widget, 实际 {len(content_box.children)}"
        )

    def test_report_preview_with_promise(self):
        """当 report_data 包含 promise 时, 渲染承诺信息。"""
        from app.models.report import PeriodDetail, PromiseDetail, ReportData

        data = ReportData(
            date="2026-06-07",
            is_shooting_day=False,
            periods=[
                PeriodDetail(
                    period="morning",
                    checkin_time="09:00",
                    checkout_time="12:00",
                    status="normal",
                    status_label="正常",
                ),
            ],
            penalty_total=0.0,
            reward_total=0.0,
            net_amount=0.0,
            total_work_hours=4.0,
            overtime_hours=0.0,
            promise=PromiseDetail(
                reward_desc="奶茶一杯",
                reward_qty=2,
                fulfilled=False,
            ),
            completed_tasks=["完成论文初稿", "跑步 5km"],
            encouragement="坚持就是胜利!",
        )
        preview = ReportPreview(
            image_path="",
            report_data=data,
            date_str="2026-06-07",
        )
        content_box = preview._content_box
        # 承诺 + 完成任务会产生更多 widget
        assert len(content_box.children) > 2, (
            f"含 promise 和 completed_tasks 时应有多个子 widget, 实际 {len(content_box.children)}"
        )

    def test_shooting_report_shows_reflection(self):
        """拍摄日战报应在 widget 树中显示复盘内容。"""
        from app.models.report import PeriodDetail, ReportData

        data = ReportData(
            date="2026-06-15",
            is_shooting_day=True,
            periods=[PeriodDetail(period="morning", status="shooting", status_label="拍摄日")],
            encouragement="加油",
            shooting_content="宣传片",
            shooting_location="创意园",
            shooting_reflection="今天在创意园顺利完成了宣传片的拍摄",
        )
        preview = ReportPreview(image_path="", report_data=data, date_str="2026-06-15")
        joined = " ".join(_all_label_texts(preview._content_box))
        assert "拍摄复盘" in joined
        assert "创意园" in joined
        assert "今天在创意园顺利完成了宣传片的拍摄" in joined

    def test_office_report_has_no_reflection_section(self):
        """办公日战报(无复盘数据)不应出现拍摄复盘 section。"""
        from app.models.report import PeriodDetail, ReportData

        data = ReportData(
            date="2026-06-15",
            is_shooting_day=False,
            periods=[PeriodDetail(period="morning", status="normal", status_label="正常")],
            encouragement="加油",
        )
        preview = ReportPreview(image_path="", report_data=data, date_str="2026-06-15")
        joined = " ".join(_all_label_texts(preview._content_box))
        assert "拍摄复盘" not in joined

    def test_shooting_report_uses_big_scene_not_grid(self):
        """拍摄日战报用一张大现场照替代六格打卡网格。"""
        from app.models.report import PeriodDetail, ReportData
        from app.ui.components.report_preview import _ReportPhotoGrid, _ShootingSceneBig

        data = ReportData(
            date="2026-06-15",
            is_shooting_day=True,
            periods=[
                PeriodDetail(period=p, status="shooting", status_label="拍摄")
                for p in ("morning", "afternoon", "evening")
            ],
            encouragement="加油",
        )
        preview = ReportPreview(image_path="", report_data=data, date_str="2026-06-15")
        assert len(_find_widgets(preview._content_box, _ShootingSceneBig)) == 1
        assert len(_find_widgets(preview._content_box, _ReportPhotoGrid)) == 0

    def test_shooting_report_with_reward_shows_amount_not_zero_hours(self):
        """真机反馈: 战报显示"小熊熬夜 今天工时0", 而不是拍摄奖励金额。

        根因: _reward_panel 的 achieved 判断只看 total_work_hours(拍摄日
        恒为 0, 不可能 >= threshold_hours), 完全没考虑拍摄日应该看
        reward_total(拍摄奖励是否已入账)。应该复用工作日达标的小猫庆祝
        模板, 文案换成拍摄奖励金额。
        """
        from app.models.report import PeriodDetail, ReportData

        data = ReportData(
            date="2026-06-15",
            is_shooting_day=True,
            periods=[PeriodDetail(period=p, status="shooting", status_label="拍摄")
                     for p in ("morning", "afternoon", "evening")],
            reward_total=30.0,
            total_work_hours=0.0,
        )
        preview = ReportPreview(image_path="", report_data=data, date_str="2026-06-15")
        joined = " ".join(_all_label_texts(preview._content_box))
        assert "熬夜" not in joined
        assert "工时 0" not in joined
        assert "拍摄奖励" in joined and "30" in joined

    def test_shooting_report_without_reward_shows_pending_message(self):
        """拍摄日复盘还没提交(尚未入账)时, 显示"还没提交"而非"工时0未达标"。"""
        from app.models.report import PeriodDetail, ReportData

        data = ReportData(
            date="2026-06-15",
            is_shooting_day=True,
            periods=[PeriodDetail(period=p, status="shooting", status_label="拍摄")
                     for p in ("morning", "afternoon", "evening")],
            reward_total=0.0,
            total_work_hours=0.0,
        )
        preview = ReportPreview(image_path="", report_data=data, date_str="2026-06-15")
        joined = " ".join(_all_label_texts(preview._content_box))
        assert "工时 0" not in joined
        assert "还没提交" in joined

    def test_office_report_still_uses_photo_grid(self):
        """办公日战报仍用六格网格(回归)。"""
        from app.models.report import PeriodDetail, ReportData
        from app.ui.components.report_preview import _ReportPhotoGrid, _ShootingSceneBig

        data = ReportData(
            date="2026-06-15",
            is_shooting_day=False,
            periods=[
                PeriodDetail(period="morning", status="normal", status_label="正常"),
                PeriodDetail(period="afternoon", status="normal", status_label="正常"),
            ],
            encouragement="加油",
        )
        preview = ReportPreview(image_path="", report_data=data, date_str="2026-06-15")
        assert len(_find_widgets(preview._content_box, _ReportPhotoGrid)) == 1
        assert len(_find_widgets(preview._content_box, _ShootingSceneBig)) == 0
