# 文字超采样 bug 复盘与修复方案(已回退,暂缓)

- 日期:2026-07-06
- 状态:**已回退**(`17ff103` 引入 → `ac32694` 回退),按 andy 决定「字体先不动」暂缓,本文仅存档根因与后续方案。
- 相关提交:`17ff103`(超采样实现)、`ac32694`(回退)、`7b64f32`(像素图 nearest,保留)

---

## 1. 背景:发糊的根源

主界面所有内容画在一个 **420 逻辑宽度**(`tokens.LOGICAL_WIDTH = 420`)的画布上,再由**单个 ScatterLayout 整体线性放大约 2.57×** 铺满真机屏幕。

后果:文字先按逻辑小字号光栅化成纹理,再被 GPU 拉大 2.57× → 边缘发糊。这与像素图用 `nearest` 是**两类问题**(像素图要硬边、文字要柔和抗锯齿),所以文字不能用 nearest,得单独处理。

## 2. 回退掉的方案做了什么

`17ff103` 借道 `fonts.py` 已有的 Label monkey-patch 入口,补丁了 `Label.texture_update`:

1. 渲染前把 core label 的 `options['font_size'] × SS`、`usersize(text_size) × SS`;
2. 调原始 `texture_update` → 得到 SS 倍分辨率的高清字形纹理;
3. `finally` 还原 font_size / usersize;
4. 渲染后 `label.texture_size = [tex.size[0] / SS, tex.size[1] / SS]` 把布局占用压回 1×。

意图:纹理是 SS 倍高清,但布局尺寸仍是 1×;经 Scatter ×SS 放大后高清纹理 1:1 落到物理像素 → 不糊。SS 由 `main.py` 按真机整体缩放比设入,桌面/测试锁 420 窗口 → SS=1 → 纯透传。

## 3. 症状

真机上「字号随机变化,有大有小,完全没法用」。而作者当时的「真机自检」其实是**桌面 `SOLOIST_WIN` 模拟**(固定 420 窗口 + 强设 SS=2.57),那里渲染次数 5→5→5→5 收敛、探针显示锐利 —— **模拟通过,真机翻车**。

## 4. 根因分析

**这不是一个一行 bug,是方案本身的架构性脆弱。**

### 4.1 主因:`texture_size` 反馈环在真机不收敛

`texture_size` 是**参与布局的活属性**。本项目里 `text_size ↔ size ↔ texture_size` 的绑定极其密集(全 `app/ui` 49 处 / 17 文件,如 IconLabel、status_box、report_preview、week_summary 等都有 `label.bind(texture_size=... setter('size'))` 一类写法)。

补丁在渲染**之后**强行改写 `texture_size`,与这些绑定构成反馈环:改 texture_size → 改 size → 改 text_size(usersize)→ 触发下一次 texture_update。每一次单独调用是自洽的(×SS 再还原),但**整个环能否收敛到同一不动点,依赖渲染的调度时序**:

- 桌面固定 420 窗口:时序稳定,环恰好收敛。
- 真机:纹理刷新是 `Clock.create_trigger(texture_update) + WeakMethod` **异步**调度,不同 label 停在反馈环的**不同迭代**上 → 表现为随机的大小不一。

### 4.2 帮凶:压回时除错了尺寸

第 4 步除的是 `label.texture.size`(**GL 纹理分配尺寸**),而不是内容尺寸 `label._label.size`。Kivy 原生 `texture_update` 用的是 `self._label.size`。桌面(NPOT、无 clamp)两者相等,安卓上纹理分配可能因驱动 clamp / 对齐而与内容尺寸不等 → 每个 label 的除法因子都可能不同 → 加剧随机大小。

### 4.3 已排除的误因(避免以后再查)

- **设备密度 sp**:`FONT_SIZE_*` 是**纯 px 整数**(`tokens.py`,非 `sp()`),不存在真机密度二次缩放。
- **markup 绝对字号 `[size=]`**:全 `app/ui` **零处**使用,不存在「基字号 ×SS 但 `[size=N]` 标签不缩」的同标签内混合。

### 4.4 流程教训

systematic-debugging 的 Phase 1「在故障环境收集证据」被跳过了 —— 用桌面模拟代替真机,恰好把决定性的时序差异掩盖掉,才让脆弱方案上了车。**下次任何"仅真机复现"的问题,证据必须来自真机(真机日志),不能用桌面模拟替代。**

## 5. 修复方案(按性价比)

| 方案 | 做法 | 评价 |
|---|---|---|
| **A. 放弃超采样(当前)** | 维持回退状态。发糊是观感问题非崩溃 | ✅ 最省心,andy 已选 |
| **B. 真机插桩 + 正确重写** | 见下 | 想保留高清再走,需完整一轮 |
| **C. 根治(大改)** | 不再把 420 小画布 Scatter ×2.57,改按真机分辨率用 dp/sp 布局,文字天然原生光栅化,无需超采样 | 一劳永逸,动整个布局体系,建议单独立项 |

### 方案 B 的关键纠正(存档备用)

1. **先真机插桩**:临时日志打每个 label 的 `font_size / _label.size / texture.size / 最终 texture_size`,真机跑一次,确认 4.1 反馈环 vs 4.2 除错尺寸谁是主因。
2. **除内容尺寸,不除纹理尺寸**:
   ```python
   # 错(回退版):label.texture_size = [tex.size[0] / ss, tex.size[1] / ss]
   # 对:orig 已把 texture_size 置为 _label.size(内容尺寸, ss 倍),直接除它
   ts = label.texture_size
   label.texture_size = [ts[0] / ss, ts[1] / ss]
   ```
3. **别 monkey-patch,用 Label 子类**:把高清渲染 + 尺寸压回收敛进一个自定义 Label 的 `texture_update` 里,`size` 显式计算、绝不回写进 `text_size` 反馈环,从根上消除 4.1 的不收敛。
4. onboarding 首屏不走 ScatterLayout,单独评估。

## 6. 当前决定

按 andy「字体先不动」:**维持方案 A(已回退)**。若日后觉得发糊难以接受,优先按**方案 C** 正经做,不要再回到 monkey-patch + 改 `texture_size` 的老路。
