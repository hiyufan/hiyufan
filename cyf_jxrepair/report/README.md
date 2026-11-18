# 项目报告生成工具

按课程附件的八章提纲生成可编辑Word报告。内容来自当前源码、OpenAPI、数据库结构、Git差异、独立实例截图及量化实验。封面个人信息从外部JSON读取，报告及学生资料不自动提交到Git。

依赖：Python3.11+、python-docx、Pillow；导出PDF另需LibreOffice。运行前将报告证据包中的assets、evidence.json、openapi.json、database-metadata.json、backend-tests.txt、frontend-tests.txt、toc-pages.json放在输出目录；算法实验引用presentation/research/results.json。

创建保存在仓库外的student-info.json：

```json
{"name":"填写姓名","student_id":"填写学号","class_name":"填写专业班级"}
```

在项目根目录执行：

```bash
python report/build_report.py --student-info /path/to/student-info.json --output-dir /path/to/report-evidence
libreoffice --headless --convert-to pdf --outdir /path/to/report-evidence /path/to/report-evidence/报告文件.docx
```

正文注明了开发集、合成语料、当前部署与本地修正的范围；AI生成的TraeCN风格工作流图只作概念示意，不当作真实软件执行证据。真实TraeCN记录、本人原始审核过程、源码注释完整性、Microsoft Edge与指定MySQL8.0环境验证仍需按实际情况补齐。

当前报告工具生成8章、44个接口表、8组修正案例、14条复核日志和35处插图引用。运行数据与测试结果均有证据文件。输出包含个人信息，公开发布前应由本人决定公开范围；默认只将工具源码入库。
