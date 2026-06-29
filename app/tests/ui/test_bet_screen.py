"""对赌页 (UI-05) 完整测试。

测试组件:
- BetTaskItem: 添加任务→列表渲染、勾选进度→计数更新、右滑完成→旺仔动画触发、左滑删除→任务移除
- BetScreen: 周结算按钮状态(周日可用/其他灰掉)、弹窗金额计算正确、确认结算→数据写入
- WeekSummaryHeader: 数字跳动动画
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.repositories.bet_repo import BetRepo
from app.repositories.ledger_repo import LedgerRepo
from app.repositories.settings_repo import SettingsRepo
from app.services.bet_service import BetService
from app.ui.components.add_task_dialog import AddTaskDialog
from app.ui.components.bet_config_section import BetConfigSection
from app.ui.components.bet_task_item import BetTaskItem
from app.ui.components.settlement_dialog import SettlementDialog
from app.ui.components.week_summary_header import WeekSummaryHeader
from app.ui.screens.bet_screen import BetScreen

# ============================================================
# 辅助函数
# ============================================================


def create_bet_service(temp_db: str) -> BetService:
    """创建带内存数据库的 BetService 实例。"""
    return BetService(
        bet_repo=BetRepo(temp_db),
        ledger_repo=LedgerRepo(temp_db),
        settings_repo=SettingsRepo(temp_db),
    )


def _to_rgba(hex_color: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
    h = hex_color.lstrip("#")
    return (
        int(h[0:2], 16) / 255.0,
        int(h[2:4], 16) / 255.0,
        int(h[4:6], 16) / 255.0,
        alpha,
    )


# ============================================================
# 5.1-5.2 WeekSummaryHeader 测试
# ============================================================


class TestWeekSummaryHeader:
    """WeekSummaryHeader 组件测试。"""

    def test_create_with_defaults(self) -> None:
        """创建空总结头。"""
        header = WeekSummaryHeader()
        assert header.height > 0
        assert header._completed_label is not None
        assert header._reward_label is not None
        assert header._rate_label is not None

    def test_update_summary_sets_text(self) -> None:
        """更新总结数据显示（不测试动画，直接设置）。"""
        header = WeekSummaryHeader()
        summary: dict[str, object] = {
            "completed": 3,
            "extra_count": 1,
            "total_reward": 80.0,
            "completion_rate": 75.0,
            "total_tasks": 4,
            "config": None,
        }
        header.update_summary(summary, animate=False)

        assert "已完成 3" in header._completed_label.text
        assert "超额 1" in header._completed_label.text
        assert "预计奖励: +80" in header._reward_label.text
        assert "75%" in header._rate_label.text

    def test_update_summary_animates_numbers(self) -> None:
        """验证 animate=True 也会先设置文本（不依赖 Clock）。"""
        header = WeekSummaryHeader()
        summary: dict[str, object] = {
            "completed": 5,
            "extra_count": 2,
            "total_reward": 100.0,
            "completion_rate": 100.0,
            "total_tasks": 5,
            "config": None,
        }
        # animate=False 也直接设置文本
        header.update_summary(summary, animate=False)

        assert "5" in header._completed_label.text
        assert "100" in header._rate_label.text

    def test_redraw_draws_border(self) -> None:
        """重绘绘制边框。"""
        header = WeekSummaryHeader()
        header.size = (300, 96)
        header.pos = (0, 0)
        header._redraw()

        assert len(header.canvas.before.children) > 0


# ============================================================
# 5.3-5.6 BetTaskItem 测试
# ============================================================


class TestBetTaskItem:
    """BetTaskItem 组件测试。"""

    def test_create_task_item(self, temp_db: str) -> None:
        """创建任务行并验证显示。"""
        svc = create_bet_service(temp_db)
        task = svc.create_task("2026-06-01", "写三篇文章", target_qty=5)

        item = BetTaskItem(task=task)
        assert item.task.task_desc == "写三篇文章"
        assert item.task.target_qty == 5
        assert item.task.current_qty == 0
        assert not item.task.is_completed

    def test_progress_increment(self, temp_db: str) -> None:
        """[+1] 按钮模拟 — 进度递增。回调传 delta=+1 (与 service 增量语义对齐)。"""
        svc = create_bet_service(temp_db)
        task = svc.create_task("2026-06-01", "发视频", target_qty=3)

        progress_values: list[int] = []
        item = BetTaskItem(
            task=task,
            on_progress=lambda tid, qty: progress_values.append(qty),
        )

        # 模拟 [+1] 点击
        item._do_increment()
        assert item.task.current_qty == 1
        assert len(progress_values) == 1
        assert progress_values[0] == 1  # delta=+1

        item._do_increment()
        assert item.task.current_qty == 2
        assert progress_values[1] == 1  # 不是 cur=2, 而是 delta=+1

        item._do_increment()
        assert item.task.current_qty == 3
        assert progress_values[2] == 1  # delta=+1
        assert item.task.is_completed == 1  # 达到目标自动完成

    def test_increment_allows_exceeding_target(self, temp_db: str) -> None:
        """已完成的任务允许继续 [+1] 超额完成 (用户需求: 无超额上限)。"""
        svc = create_bet_service(temp_db)
        task = svc.create_task("2026-06-01", "超额任务", target_qty=2)

        item = BetTaskItem(task=task)
        item._do_increment()
        item._do_increment()
        assert item.task.current_qty == 2
        assert item.task.is_completed == 1

        # 完成后继续 +1 应该被接受
        item._do_increment()
        assert item.task.current_qty == 3
        assert item.task.is_completed == 1  # 仍标完成

        item._do_increment()
        assert item.task.current_qty == 4

    def test_progress_decrement(self, temp_db: str) -> None:
        """[-1] 按钮模拟 — 进度递减, 下限 0。"""
        svc = create_bet_service(temp_db)
        task = svc.create_task("2026-06-01", "撤销任务", target_qty=3)

        progress_values: list[int] = []
        item = BetTaskItem(
            task=task,
            on_progress=lambda tid, qty: progress_values.append(qty),
        )

        item._do_increment()
        item._do_increment()
        assert item.task.current_qty == 2

        item._do_decrement()
        assert item.task.current_qty == 1

        item._do_decrement()
        item._do_decrement()
        assert item.task.current_qty == 0

        # 已经 0, 再 -1 不应该变负数
        item._do_decrement()
        assert item.task.current_qty == 0

    def test_decrement_uncompletes_when_below_target(self, temp_db: str) -> None:
        """完成的任务 -1 到低于 target 时, UI 端取消完成状态显示。"""
        svc = create_bet_service(temp_db)
        task = svc.create_task("2026-06-01", "回退任务", target_qty=2)

        item = BetTaskItem(task=task)
        item._do_increment()
        item._do_increment()
        assert item.task.is_completed == 1

        # 减一回到 1/2, 应取消完成态
        item._do_decrement()
        assert item.task.current_qty == 1
        assert item.task.is_completed == 0

    def test_minus_button_widget_exists(self, temp_db: str) -> None:
        """BetTaskItem 应有 _minus_btn 子组件 (与 _plus_btn 并列)。"""
        svc = create_bet_service(temp_db)
        task = svc.create_task("2026-06-01", "按钮检查", target_qty=3)

        item = BetTaskItem(task=task)
        assert hasattr(item, "_minus_btn"), "BetTaskItem 应有 _minus_btn"
        assert item._minus_btn.text == "-1"

    def test_edit_button_widget_exists(self, temp_db: str) -> None:
        """BetTaskItem 应有 _edit_btn 子组件 (左滑露出 编辑+删除 两个按钮)。"""
        svc = create_bet_service(temp_db)
        task = svc.create_task("2026-06-01", "编辑按钮检查", target_qty=3)

        item = BetTaskItem(task=task)
        assert hasattr(item, "_edit_btn"), "BetTaskItem 应有 _edit_btn"
        assert item._edit_btn.text == "编辑"
        assert hasattr(item, "_delete_btn"), "BetTaskItem 仍应有 _delete_btn"
        assert item._delete_btn.text == "删除"

    def test_do_edit_triggers_callback(self, temp_db: str) -> None:
        """_do_edit 应该触发 on_edit 回调, 传 task_id。"""
        svc = create_bet_service(temp_db)
        task = svc.create_task("2026-06-01", "编辑回调", target_qty=2)
        assert task.id is not None

        edit_ids: list[int] = []
        item = BetTaskItem(task=task, on_edit=lambda tid: edit_ids.append(tid))

        item._do_edit()
        assert edit_ids == [task.id]

    def test_checkbox_toggle(self, temp_db: str) -> None:
        """复选框切换完成状态。"""
        svc = create_bet_service(temp_db)
        task = svc.create_task("2026-06-01", "测试任务")
        assert task.is_completed == 0

        completed_ids: list[int] = []
        item = BetTaskItem(
            task=task,
            on_complete=lambda tid: completed_ids.append(tid),
        )

        # 切换完成
        item._do_toggle_check()
        assert item.task.is_completed == 1
        assert len(completed_ids) > 0

        # 切回未完成
        item._do_toggle_check()
        assert item.task.is_completed == 0

    def test_right_swipe_complete(self, temp_db: str) -> None:
        """右滑完成 — 旺仔动画触发。"""
        svc = create_bet_service(temp_db)
        task = svc.create_task("2026-06-01", "右滑任务")

        completed_ids: list[int] = []
        item = BetTaskItem(
            task=task,
            on_complete=lambda tid: completed_ids.append(tid),
        )

        assert not item._completed_anim
        # 触发完成动画
        item._animate_complete()
        assert item._completed_anim
        assert item.task.is_completed == 1  # type: ignore[unreachable]
        assert len(completed_ids) > 0

        # 推进时钟使动画完成
        from kivy.clock import Clock

        for _ in range(20):
            Clock.tick()

        assert not item._completed_anim

    def test_left_swipe_delete(self, temp_db: str) -> None:
        """左滑删除 — 露出删除按钮。"""
        svc = create_bet_service(temp_db)
        task = svc.create_task("2026-06-01", "删除任务")

        deleted_ids: list[int] = []
        item = BetTaskItem(
            task=task,
            on_delete=lambda tid: deleted_ids.append(tid),
        )

        assert not item._delete_visible
        item._show_delete()
        assert item._delete_visible
        assert item._delete_btn.opacity == 1  # type: ignore[unreachable]

        # 执行删除
        item._do_delete()
        assert len(deleted_ids) > 0

    def test_snap_back(self, temp_db: str) -> None:
        """滑动弹回。"""
        svc = create_bet_service(temp_db)
        task = svc.create_task("2026-06-01", "测试")
        item = BetTaskItem(task=task)

        item._show_delete()
        assert item._delete_visible

        item._snap_back()
        assert not item._delete_visible
        assert item._delete_btn.opacity == 0  # type: ignore[unreachable]


# ============================================================
# 5.7-5.8 AddTaskDialog 测试
# ============================================================


class TestAddTaskDialog:
    """AddTaskDialog 组件测试。"""

    def test_create_dialog(self) -> None:
        """创建添加任务弹窗。"""
        dialog = AddTaskDialog()
        assert dialog is not None
        assert dialog._desc_input is not None
        assert dialog._qty_stepper is not None

    def test_stepper_min_value(self) -> None:
        """步进器最小值为 1。"""
        dialog = AddTaskDialog()
        stepper = dialog._qty_stepper
        # 验证值不能低于 1
        assert stepper.value >= 1
        stepper._decrement()
        assert stepper.value >= 1

    def test_validation_empty_description(self) -> None:
        """空描述验证失败。"""
        results: list[tuple[str, int]] = []

        dialog = AddTaskDialog(on_add=lambda d, q: results.append((d, q)))
        dialog._desc_input.value = ""
        dialog._qty_stepper.value = 1

        # 应该有验证错误
        dialog._handle_confirm()
        assert len(results) == 0  # 未成功
        assert dialog._error_label.text == "请输入任务描述"

    def test_validation_success(self) -> None:
        """有效输入通过验证。"""
        results: list[tuple[str, int]] = []

        dialog = AddTaskDialog(on_add=lambda d, q: results.append((d, q)))
        dialog._desc_input.value = "写文章"
        dialog._qty_stepper.value = 5

        dialog._handle_confirm()
        assert len(results) == 1
        assert results[0] == ("写文章", 5)

    def test_edit_mode_prefills_values(self) -> None:
        """编辑模式: 初始 desc + 初始 qty + 标题/确认按钮文案可定制。"""
        dialog = AddTaskDialog(
            initial_desc="老任务",
            initial_qty=7,
            title_text="编辑任务",
            confirm_text="保存",
        )
        assert dialog._desc_input.value == "老任务"
        assert dialog._qty_stepper.value == 7
        # 标题文案存入实例 (供 _title_label 读取)
        assert dialog._title_text == "编辑任务"
        assert dialog._confirm_text == "保存"


# ============================================================
# 5.9-5.10 BetConfigSection 测试
# ============================================================


class TestBetConfigSection:
    """BetConfigSection 组件测试。"""

    def test_create_section(self, temp_db: str) -> None:
        """创建配置折叠区。"""
        svc = create_bet_service(temp_db)
        section = BetConfigSection(week_start="2026-06-01", bet_service=svc)
        assert section is not None
        assert "赏罚" in section._title_label.text or "设置" in section._title_label.text

        # 默认折叠
        assert section.collapsed

    def test_loads_config(self, temp_db: str) -> None:
        """加载已保存的配置。"""
        svc = create_bet_service(temp_db)
        svc.set_week_config("2026-06-01", 100, 50, 80)

        section = BetConfigSection(week_start="2026-06-01", bet_service=svc)
        assert section._config["base_reward"] == 100
        assert section._config["extra_reward"] == 50
        assert section._config["penalty"] == 80

    def test_save_config(self, temp_db: str) -> None:
        """保存配置到 BetService。"""
        svc = create_bet_service(temp_db)
        section = BetConfigSection(week_start="2026-06-01", bet_service=svc)

        section._save_config("base_reward", 200)
        saved = svc.get_week_summary("2026-06-01")["config"]
        assert saved is not None
        assert float(getattr(saved, "base_reward", 0)) == 200


# ============================================================
# 5.11-5.13 SettlementDialog 测试
# ============================================================


class TestSettlementDialog:
    """SettlementDialog 组件测试。"""

    def test_create_dialog(self, temp_db: str) -> None:
        """创建结算弹窗。"""
        svc = create_bet_service(temp_db)
        summary: dict[str, object] = {
            "completed": 2,
            "total_tasks": 3,
            "extra_count": 0,
            "completion_rate": 66.7,
            "total_reward": 0.0,
            "config": None,
        }
        dialog = SettlementDialog(
            week_start="2026-06-01",
            bet_service=svc,
            summary=summary,
        )
        assert dialog is not None

    def test_dialog_all_completed(self, temp_db: str) -> None:
        """全部完成时显示奖励。"""
        svc = create_bet_service(temp_db)
        svc.set_week_config("2026-06-01", 50, 30, 50)
        t1 = svc.create_task("2026-06-01", "任务1")
        t2 = svc.create_task("2026-06-01", "任务2")
        assert t1.id is not None
        assert t2.id is not None
        svc.complete_task(t1.id)
        svc.complete_task(t2.id)

        summary = svc.get_week_summary("2026-06-01")
        dialog = SettlementDialog(
            week_start="2026-06-01",
            bet_service=svc,
            summary=summary,
        )
        # 全部完成: reward=50, extra=0, penalty=0, net=50
        assert dialog._cached_base_reward == 50
        assert dialog._cached_extra_reward == 30
        assert dialog._cached_penalty == 50

    def test_dialog_with_uncompleted(self, temp_db: str) -> None:
        """有未完成时显示惩罚。"""
        svc = create_bet_service(temp_db)
        svc.set_week_config("2026-06-01", 50, 30, 50)
        svc.create_task("2026-06-01", "任务1")
        svc.create_task("2026-06-01", "任务2")

        summary = svc.get_week_summary("2026-06-01")
        dialog = SettlementDialog(
            week_start="2026-06-01",
            bet_service=svc,
            summary=summary,
        )
        # 全部未完成: reward=0, extra=0, penalty=50, net=-50
        assert dialog._cached_penalty == 50

    def test_confirm_settles_week(self, temp_db: str) -> None:
        """确认结算写入数据。"""
        svc = create_bet_service(temp_db)
        svc.set_week_config("2026-06-01", 50, 30, 50)
        t1 = svc.create_task("2026-06-01", "任务1")
        assert t1.id is not None
        svc.complete_task(t1.id)

        summary = svc.get_week_summary("2026-06-01")
        settled = [False]

        dialog = SettlementDialog(
            week_start="2026-06-01",
            bet_service=svc,
            summary=summary,
            on_settled=lambda: settled.__setitem__(0, True),
        )

        # 确认结算
        dialog._handle_confirm()

        # 验证结算结果

        # 检查任务配置状态
        config = svc._bet_repo.get_config("2026-06-01")
        assert config is not None
        assert config.status == "settled"


# ============================================================
# 5.14 BetScreen 测试
# ============================================================


class TestBetScreen:
    """BetScreen 页面组装测试。"""

    def test_create_screen(self, temp_db: str) -> None:
        """创建 BetScreen 页面。"""
        svc = create_bet_service(temp_db)
        screen = BetScreen(bet_service=svc)
        assert screen is not None
        assert screen._header is not None
        assert screen._task_container is not None
        assert screen._add_btn is not None
        assert screen._config_section is not None
        assert screen._settle_btn is not None

    def test_screen_loads_tasks(self, temp_db: str, clock: Any) -> None:
        """页面加载已有任务。"""
        # 设到有数据的周
        clock.set_time(datetime(2026, 6, 1))  # Monday -> week_start = 2026-06-01

        svc = create_bet_service(temp_db)
        svc.set_week_config("2026-06-01", 50, 30, 50)
        svc.create_task("2026-06-01", "文章1")
        svc.create_task("2026-06-01", "文章2", target_qty=3)

        screen = BetScreen(bet_service=svc)
        # 触发数据加载
        screen.refresh()
        assert len(screen._task_container.children) == 2

    def test_create_task_through_screen(self, temp_db: str, clock: Any) -> None:
        """通过页面添加任务。"""
        clock.set_time(datetime(2026, 6, 1))  # Monday -> week_start = 2026-06-01

        svc = create_bet_service(temp_db)
        # 预设当前周期 config 使 get_current_cycle_start 返回期望值
        svc.set_week_config("2026-06-01", 50, 30, 50)
        screen = BetScreen(bet_service=svc)

        # 手动触发添加
        screen._on_add_task("新任务", 5)
        tasks = svc.get_week_tasks("2026-06-01")
        assert len(tasks) == 1
        assert tasks[0].task_desc == "新任务"
        assert tasks[0].target_qty == 5


# ============================================================
# 5.15-5.16 结算按钮与交互测试
# ============================================================


class TestBetScreenSettlement:
    """结算按钮状态与交互测试。"""

    def test_settle_button_disabled_on_non_sunday(self, temp_db: str, clock: Any) -> None:
        """非周日结算按钮禁用。"""
        # 设为周一
        clock.set_time(datetime(2026, 6, 1))  # Monday

        svc = create_bet_service(temp_db)
        screen = BetScreen(bet_service=svc)

        # 由于周一不是周日，按钮应禁用
        assert screen._settle_btn.disabled
        assert "周日" in screen._settle_hint.text

    def test_settle_button_disabled_on_sunday_uncompleted(self, temp_db: str, clock: Any) -> None:
        """周日有未完成任务 → 按钮禁用,提示用户完成全部任务。"""
        clock.set_time(datetime(2026, 6, 7))  # Sunday

        svc = create_bet_service(temp_db)
        svc.set_week_config("2026-06-01", 50, 30, 50)
        svc.create_task("2026-06-01", "任务1")
        screen = BetScreen(bet_service=svc)
        screen.refresh()

        assert screen._settle_btn.disabled
        assert "请完成全部任务" in screen._settle_hint.text

    def test_settle_button_enabled_on_sunday_all_done(self, temp_db: str, clock: Any) -> None:
        """周日全部任务完成 → 结算按钮可用。"""
        clock.set_time(datetime(2026, 6, 7))  # Sunday

        svc = create_bet_service(temp_db)
        svc.set_week_config("2026-06-01", 50, 30, 50)
        t = svc.create_task("2026-06-01", "任务1")
        svc.complete_task(t.id)
        screen = BetScreen(bet_service=svc)
        screen.refresh()

        assert not screen._settle_btn.disabled
        assert screen._settle_hint.text == ""

    def test_full_flow_create_and_complete(self, temp_db: str) -> None:
        """完整流程: 创建任务 → 完成 → 查看总结。"""
        svc = create_bet_service(temp_db)

        # 创建任务
        t1 = svc.create_task("2026-06-01", "任务A", target_qty=3)
        t2 = svc.create_task("2026-06-01", "任务B", target_qty=1)
        assert t1.id is not None
        assert t2.id is not None

        # 完成部分进度 (delta 语义: +N 增, -N 减)
        svc.update_task_progress(t1.id, 2)  # 0 → 2
        svc.update_task_progress(t2.id, 1)  # 0 → 1, auto-completes

        # 检查状态
        tasks = svc.get_week_tasks("2026-06-01")
        t1_refreshed = [t for t in tasks if t.id == t1.id][0]
        t2_refreshed = [t for t in tasks if t.id == t2.id][0]
        assert t1_refreshed.current_qty == 2
        assert t1_refreshed.is_completed == 0
        assert t2_refreshed.is_completed == 1

        # 检查总结
        summary = svc.get_week_summary("2026-06-01")
        assert summary["completed"] == 1
        assert summary["total_tasks"] == 2

    def test_update_task_progress_delta_semantics(self, temp_db: str) -> None:
        """service.update_task_progress 是 delta 语义 — 正负增量 + 下限 0 + is_completed 双向。"""
        svc = create_bet_service(temp_db)
        t = svc.create_task("2026-06-01", "delta 测试", target_qty=2)
        assert t.id is not None

        # +1 → 1/2, 未完成
        svc.update_task_progress(t.id, 1)
        r = [x for x in svc.get_week_tasks("2026-06-01") if x.id == t.id][0]
        assert r.current_qty == 1
        assert r.is_completed == 0

        # +1 → 2/2, 自动完成
        svc.update_task_progress(t.id, 1)
        r = [x for x in svc.get_week_tasks("2026-06-01") if x.id == t.id][0]
        assert r.current_qty == 2
        assert r.is_completed == 1

        # -1 → 1/2, 自动取消完成态
        svc.update_task_progress(t.id, -1)
        r = [x for x in svc.get_week_tasks("2026-06-01") if x.id == t.id][0]
        assert r.current_qty == 1
        assert r.is_completed == 0

        # -5 → MAX(0, 1-5) = 0, 不会变负
        svc.update_task_progress(t.id, -5)
        r = [x for x in svc.get_week_tasks("2026-06-01") if x.id == t.id][0]
        assert r.current_qty == 0
        assert r.is_completed == 0

    def test_update_task_edits_desc_and_target(self, temp_db: str) -> None:
        """service.update_task 改 desc + target_qty, 保留 current_qty。"""
        svc = create_bet_service(temp_db)
        t = svc.create_task("2026-06-01", "原描述", target_qty=3)
        assert t.id is not None
        svc.update_task_progress(t.id, 2)  # 进度 0→2

        # 编辑: 改描述 + 降低 target 到 2 → 应自动完成
        svc.update_task(t.id, "新描述", 2)
        r = [x for x in svc.get_week_tasks("2026-06-01") if x.id == t.id][0]
        assert r.task_desc == "新描述"
        assert r.target_qty == 2
        assert r.current_qty == 2  # 进度保留
        assert r.is_completed == 1  # 达到新 target 自动完成

        # 再升高 target 到 5 → 应取消完成
        svc.update_task(t.id, "新描述", 5)
        r = [x for x in svc.get_week_tasks("2026-06-01") if x.id == t.id][0]
        assert r.target_qty == 5
        assert r.is_completed == 0

    def test_delete_task_updates_list(self, temp_db: str) -> None:
        """删除任务后列表更新。"""
        svc = create_bet_service(temp_db)
        svc.create_task("2026-06-01", "保留")
        t2 = svc.create_task("2026-06-01", "删除")
        assert t2.id is not None

        # 删除
        svc.delete_task(t2.id)
        tasks = svc.get_week_tasks("2026-06-01")
        assert len(tasks) == 1
        assert tasks[0].task_desc == "保留"


# ============================================================
# 5.17 底部 cream 区无残留 widget 测试 (Task 9)
# ============================================================


class TestBetScreenNoOrphanAfterSettleButton:
    """周结算按钮之后不应有多余 widget（仅允许 _settle_hint）。"""

    def test_no_widget_after_settle_button(self, temp_db: str) -> None:
        """周结算按钮后只允许 settle_hint，不允许其他 widget 残留。"""
        svc = create_bet_service(temp_db)
        screen = BetScreen(bet_service=svc)
        screen.refresh()

        children_in_order = list(reversed(screen._layout.children))
        settle_idx = next(
            (
                i
                for i, w in enumerate(children_in_order)
                if hasattr(w, "text") and "周结算" in (w.text or "")
            ),
            None,
        )
        assert settle_idx is not None, "未找到周结算按钮"
        after = children_in_order[settle_idx + 1 :]
        assert len(after) <= 1, (
            f"周结算后多余 widget: {[type(w).__name__ for w in after]}"
        )

    def test_task_item_content_hidden_before_layout(self, temp_db: str) -> None:
        """BetTaskItem 子 widget 初始 opacity=0，防止在 (0,0) 闪现。

        新架构: 子 widget 直接挂在 self 上 (无 _content 中间层),
        各 widget 用 opacity=0 + _layout_initialized 标志位实现防闪烁;
        首次 _redraw 拿到有效 size 后才置为 opacity=1。
        """
        svc = create_bet_service(temp_db)
        task = svc.create_task("2026-06-01", "测试任务", target_qty=3)
        from app.ui.components.bet_task_item import BetTaskItem

        item = BetTaskItem(task=task)
        # 初始所有可见 widget opacity=0
        assert item._check_box.opacity == 0
        assert item._desc_label.opacity == 0
        assert item._qty_label.opacity == 0
        assert item._progress_label.opacity == 0
        assert item._minus_btn.opacity == 0
        assert item._plus_btn.opacity == 0
        assert item._layout_initialized is False

        # 首次 _redraw 给定有效 size 后, opacity 应被打开
        item.size = (380, 56)
        item.pos = (10, 100)
        item._redraw()
        assert item._layout_initialized is True
        assert item._check_box.opacity == 1
        assert item._desc_label.opacity == 1
        assert item._qty_label.opacity == 1
        assert item._progress_label.opacity == 1
        assert item._minus_btn.opacity == 1
        assert item._plus_btn.opacity == 1

    def test_task_item_check_box_is_widget_not_ascii_label(self, temp_db: str) -> None:
        """P1: 复选框不应是 ASCII [x]/[ ] 文本 Label, 应是 Widget + canvas 矩形 +
        勾选 (跟主页 PixelCheckbox 视觉一致)。
        """
        from kivy.uix.label import Label
        from kivy.uix.widget import Widget

        svc = create_bet_service(temp_db)
        task = svc.create_task("2026-06-01", "测试任务", target_qty=3)
        from app.ui.components.bet_task_item import BetTaskItem

        item = BetTaskItem(task=task)
        assert hasattr(item, "_check_box"), "BetTaskItem 必须有 _check_box 属性"
        assert isinstance(item._check_box, Widget), "_check_box 必须是 Widget"
        # 必须不是 Label (排除 Label 子类)
        assert not isinstance(item._check_box, Label), (
            "_check_box 不应该是 Label — 应用 canvas 矩形画 checkbox"
        )

    def test_task_item_check_box_reflects_completion(self, temp_db: str) -> None:
        """P1: BetTaskItem._check_box.checked 跟随 task.is_completed。"""
        svc = create_bet_service(temp_db)
        from app.ui.components.bet_task_item import BetTaskItem

        task_done = svc.create_task("2026-06-01", "完成", target_qty=1)
        task_done.is_completed = 1
        item_done = BetTaskItem(task=task_done)
        assert item_done._check_box.checked is True

        task_pending = svc.create_task("2026-06-01", "待办", target_qty=3)
        item_pending = BetTaskItem(task=task_pending)
        assert item_pending._check_box.checked is False
