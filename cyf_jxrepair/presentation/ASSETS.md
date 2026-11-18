# 素材与视觉基准

封面采用工业杂志版式：大字、暖灰纸底、黑白机械臂、荧光黄绿、朱红标点、细分隔线、底部描边字。其余页面沿用同一组字体和颜色，以共享工单和连接线贯穿。十一页主标题、工单和控制器均为原生HTML，未把静态设计图作为整张幻灯片。

## 生成视觉

使用内置 ImageGen，未使用CLI/API密钥流程。设计概念保存在本次会话的生成图目录；项目实际引用的成品为 `assets/robot.png`。封面摄影是生成视觉，不表示真实企业的生产现场。

封面概念提示词：

> Create one sophisticated 16:9 widescreen Chinese software project presentation COVER DESIGN concept, 1600x900 composition, editorial industrial magazine meets high-end sci-fi strategy game typography, absolutely no generic PowerPoint cards. Warm pale ivory #efece4 background, almost black #181c19 ink, acid lime #dfff66 accent, sparse red-orange #f25b3b. Very large heavy Chinese sans serif title at left, exact text: '让故障，' on first line and '有下文。' on second line. Small but confidently sized product name near upper left exact text 'CYF 捷修云'. Large monochrome industrial robotic arm / CNC workshop photographic artwork occupying the right half, stark dramatic side lighting, realistic metal, hard editorial cutout edges, not cartoon, not abstract 3D blob. A vertical thin lime ruled line connects a single editorial work-order slip on lower right: exact text 'CYF20261118001', '气压不足', '待派单'. Order slip is ivory, black typographic, fine ruled form lines, crisp squared corners, no drop shadow UI cards. Huge cropped outlined Latin word REPAIR along bottom, minimal thin rules, a single oversized black page number '01' lower left. The photo and the typography each have room to breathe. No header navigation menu, no invented UI controls, no small explanatory subtitle, no eyebrow badge, no paragraphs, no charts, no QR. Think art-directed collectible technical magazine cover, exceptionally polished, typography forward. Produce one full-slide composition, all key title text entirely within margins. This is a visual concept for a code-native animated HTML presentation; later actual text will be recreated in HTML. Preserve high contrast and precise simple geometry.

机械臂成品提示词（以封面概念作为参考）：

> Create the standalone production PHOTOGRAPH asset for this exact cover concept. Preserve the industrial articulated robotic arm seen on the RIGHT side of the reference: realistic articulated metal CNC robot with wiring and weathered machined steel, dramatic workshop window sidelight, fine monochrome silver and charcoal tones, a hint of background workshop depth, high contrast but readable metal. Recompose as a clean 4:5 portrait photograph with the robotic shoulder upper right, articulated arm reaching toward left-center, tool head above machine table near lower left. FULL BLEED PHOTO ONLY. Remove ALL Chinese and English typography, ALL page numbers, ALL lime lines and colored accents, ALL order slips, ALL paper backgrounds and design graphics. Do not invent new objects or a second robot. No labels, watermarks, readable text, logos, graphic UI, or frames. We will place this separate photo asset into the right panel of a code-native HTML presentation that follows the supplied cover.

## 项目截图

`dashboard.png`、`report.png`、`order.png`、`knowledge.png`、`docs.png`均在2026-11-18从当前线上项目采集。正文使用看板、报修和真实归档工单截图；知识库与接口文档截图保留在源码素材中供后续编辑。单文件HTML只嵌入实际使用的素材。

## 文字与字体

正文基于当前源码、OpenAPI、测试结果与用户提供的两份DOCX。照片和图表未用来生成虚构业绩数据。Noto Sans SC用于中文，Barlow Condensed用于大数字，IBM Plex Mono用于工单与接口；均采用OFL许可。中文字体仅裁减字形以减小体积，保留可变字重与授权信息。
