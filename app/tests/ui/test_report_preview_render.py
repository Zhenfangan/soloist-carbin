"""测试 ReportPreview 用 Kivy widget 渲染 ReportData。"""
from __future__ import annotations

from app.ui.components.report_preview import ReportPreview


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
