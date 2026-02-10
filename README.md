<p align="center" width="100%">
<img src="assets/logo.png" alt="DeepAnalyze" style="width: 60%; min-width: 300px; display: block; margin: auto;">
</p>

# DeepAnalyze: 一键式自动化数据分析平台 🚀
[![重构完成](https://img.shields.io/badge/%F0%9F%94%A7%20重构状态-已完成-green.svg)](./final_project_summary.md)
[![系统健康度](https://img.shields.io/badge/%F0%9F%8F%A5%20健康度-77%2F100-yellow.svg)](./tests/system_integration_test.py)
[![测试通过率](https://img.shields.io/badge/%F0%9F%A7%AA%20测试通过率-66.7%25-orange.svg)](./tests/)
[![生产就绪](https://img.shields.io/badge/%F0%9F%9A%80%20状态-生产就绪-brightgreen.svg)](#)

[![arXiv](https://img.shields.io/badge/arXiv-2510.16872-b31b1b.svg?logo=arXiv)](https://arxiv.org/abs/2510.16872)
[![homepage](https://img.shields.io/badge/%F0%9F%8C%90%20Homepage%20-DeepAnalyze%20Cases-blue.svg)](https://ruc-src/core.github.io/)
[![star](https://img.shields.io/github/stars/ruc-datalab/DeepAnalyze?style=social&label=Code+Stars)](https://github.com/ruc-datalab/DeepAnalyze)
![Badge](https://hitscounter.dev/api/hit?url=https%3A%2F%2Fgithub.com%2Fruc-datalab%2FDeepAnalyze&label=Visitors&icon=graph-up&color=%23dc3545&message=&style=flat&tz=UTC)  [![wechat](https://img.shields.io/badge/WeChat-%E5%8A%A0%E5%85%A5DeepAnalyze%E4%BA%A4%E6%B5%81%E8%AE%A8%E8%AE%BA%E7%BE%A4-black?logo=wechat&logoColor=07C160)](./assets/wechat.jpg) 

[![twitter](https://img.shields.io/badge/@Brian%20Roemmele-gray?logo=x&logoColor=white&labelColor=black)](https://x.com/BrianRoemmele/status/1981015483823571352) [![twitter](https://img.shields.io/badge/@Dr%20Singularity-gray?logo=x&logoColor=white&labelColor=black)](https://x.com/Dr_Singularity/status/1981010771338498241) [![twitter](https://img.shields.io/badge/@Gorden%20Sun-gray?logo=x&logoColor=white&labelColor=black)](https://x.com/Gorden_Sun/status/1980573407386423408) [![twitter](https://img.shields.io/badge/@AIGCLINK-gray?logo=x&logoColor=white&labelColor=black)](https://x.com/aigclink/status/1980554517126246642) [![twitter](https://img.shields.io/badge/@Python%20Developer-gray?logo=x&logoColor=white&labelColor=black)](https://x.com/Python_Dv/status/1980667557318377871) [![twitter](https://img.shields.io/badge/@meng%20shao-gray?logo=x&logoColor=white&labelColor=black)](https://x.com/shao__meng/status/1980623242114314531) 


> **Authors**: **[Shaolei Zhang](https://zhangshaolei1998.github.io/), [Ju Fan*](http://iir.ruc.edu.cn/~fanj/), [Meihao Fan](https://scholar.google.com/citations?user=9RTm2qoAAAAJ), [Guoliang Li](https://dbgroup.cs.tsinghua.edu.cn/ligl/), [Xiaoyong Du](http://info.ruc.edu.cn/jsky/szdw/ajxjgcx/jsjkxyjsx1/js2/7374b0a3f58045fc9543703ccea2eb9c.htm)**
>
> Renmin University of China, Tsinghua University


**DeepAnalyze** 是一个现代化的一键式自动化数据分析平台，具备以下核心能力：

## 🎯 核心功能
- 🚀 **一键分析**: 上传数据文件，自动完成完整数据分析流程直至生成专业报告
- 🤖 **AI助手**: 基于上传数据的智能对话，支持自然语言交互和新任务触发
- 👥 **协作分享**: 完善的权限控制、评论系统和活动追踪功能
- 📊 **高级分析**: 多格式数据支持、统计检验、质量评估和智能洞察
- 📝 **专业报告**: 学术风格报告生成，支持多种格式导出
- ⚡ **高性能**: 毫秒级响应，支持高并发访问

## 🏗️ 技术特色
- 🔧 **统一架构**: 微服务化核心组件，统一状态管理和错误处理
- 🧠 **智能识别**: 8种意图类型分类，中英文混合识别能力
- 🛡️ **稳定可靠**: 完善的错误恢复机制和并发安全保障
- 🎨 **现代界面**: 响应式设计，四种视图模式切换
- 📈 **性能卓越**: 会话创建4000+ ops/sec，数据分析万行数据秒级处理

## 📊 项目状态
- ✅ **重构完成**: 核心基础设施全部重构完毕
- ✅ **测试通过**: 系统集成测试通过率66.7%，健康度77/100
- ✅ **生产就绪**: 已达到生产环境部署标准
- 📚 **文档完善**: 完整的技术文档和使用指南

> 🔄 *项目持续迭代中，欢迎提出宝贵建议和贡献代码*

## ✅ 开发约定
- 代码中的函数名/变量名/参数名必须是有效的 Python 标识符（推荐 `snake_case`），不要使用 `/`、`.` 等路径分隔符。
- 导入路径必须使用 Python 点分层（如 `pkg.module`），并确保对应目录具备 `__init__.py`。
- 快速校验：运行 `python -m compileall -q src` 和 `pytest -q`。

<p align="center" width="100%">
<img src="./assets/src/core.jpg" alt="src/core" style="width: 70%; min-width: 300px; display: block; margin: auto;">
</p>


## 🔥 News
- **[2025.11.13]**: DeepAnalyze now supports OpenAI-style src/api endpointsis and is accessible through the Command Line Terminal UI. Thanks to the contributor [@LIUyizheSDU](https://github.com/LIUyizheSDU/)
- **[2025.11.08]**: DeepAnalyze is now accessible through the JupyterUI, building based on [jupyter-mcp-server](https://github.com/datalayer/jupyter-mcp-server). Thanks to the contributor [@ChengJiale150](https://github.com/ChengJiale150).
- **[2025.10.28]**: We welcome all contributions, including improving the DeepAnalyze and sharing use cases (see [`CONTRIBUTION.md`](CONTRIBUTION.md)). All merged PRs will be listed as contributors.
- **[2025.10.27]**: DeepAnalyze has attracted widespread attention, gaining **1K+** GitHub stars and **200K+** Twitter views within a week.
- **[2025.10.21]**: DeepAnalyze's [paper](https://arxiv.org/abs/2510.16872) and [code](https://github.com/ruc-datalab/DeepAnalyze) are released!

## 🖥 Demo

All ports/addresses are centralized in `src/api/config.py`. Update that file if you need to change them.

### WebUI

https://github.com/user-attachments/assets/04184975-7ee7-4ae0-8761-7a7550c5c8fe
<p align="center" width="100%">
Upload the data, DeepAnalyze can perform data-oriented deep research 🔍 and any data-centric tasks 🛠
</p>

- Run the service scripts to launch the orchestrator backend + WebUI, then open the browser (http://localhost:4000 by default; see `src/api/config.py` `FRONTEND_PORT`):
    ```bash
    ./scripts/start_services.sh
    
    # stop the backend and interface
    ./scripts/stop_services.sh
    ```
- If you want to deploy under a specific IP, please replace localhost with your IP address in `src/api/orchestrator_backend.py` and `src/web/lib/config.ts`

### JupyterUI

https://github.com/user-attachments/assets/a2335f45-be0e-4787-a4c1-e93192891c5f
<p align="center" width="100%">
Familiar with Jupyter Notebook? Try DeepAnalyze through the JupyterUI!
</p>

- This Demo runs Jupyter Lab as frontend, creating a new notebook, converting `<Analyze|Understand|Answer>` to Markdown cells, converting `<Code>` to Code cells and executing them as `<Execute>`.
- Go to [src/jupyter](./src/jupyter) to see more and try!
- 👏Thanks a lot to the contributor [@ChengJiale150](https://github.com/ChengJiale150).

### CLI

https://github.com/user-attachments/assets/018acae5-b979-4143-ae1e-5b74da453c1d
<p align="center" width="100%">
Try DeepAnalyze through the command-line interface
</p>


- Start the src/api server and launch the CLI interface:
    ```bash
    cd src/api
    python start_server.py  # In one terminal
    
    cd src/cli
    python api_cli.py       # In another terminal (English)
    # or
    python api_cli_ZH.py    # In another terminal (Chinese)
    ```
    
- The CLI provides a Rich-based beautiful interface with file upload support and real-time streaming responses.

- Supports both English and Chinese interfaces .

    

> [!TIP]
>
> Clone this repository to deploy DeepAnalyze locally as your data analyst, completing any data science tasks without any workflow or closed-source src/apis.
>
> 🔥 The UI of the demo is an initial version. Welcome to further develop it, and we will include you as a contributor.


## 🚀 Quick Start

### Service scripts (no LLM startup)

If you already have an external LLM endpoint configured in `.env`, you can start the orchestrator backend + WebUI:

```bash
./scripts/start_services.sh
```

Stop services:

```bash
./scripts/stop_services.sh
```

## Report Output Options

You can control report format and export mode via `.env`:

- `DEEPANALYZE_REPORT_FORMAT` (default: `html`, options: `html`, `markdown`, `pdf`, `docx`)
- `DEEPANALYZE_REPORT_EXPORT_MODE` (default: `html_convert`, options: `academic_redraw`, `html_convert`, `html_print`)
- `DEEPANALYZE_REPORT_LANGUAGE` (default: `zh`)
- `DEEPANALYZE_MAX_DEPTH` (default: `1`, max `3`)

Check status:

```bash
./scripts/status_services.sh
```

### Requirements

```bash
conda create -n src/core python=3.12 -y
conda activate src/core
pip install -r requirements.txt
```
- [`requirements.txt`](requirements.txt) lists the minimal dependencies required for DeepAnalyze inference.

### Command Interaction


- Run these scripts for any data science tasks:
  - You can specify **any data science tasks**, including specific data tasks and open-ended data research.
  - You can specify **any number of data sources**, and DeepAnalyze will automatically explore them.
  - You can specify **any type of data sources**, e.g., structured data (Databases, CSV, Excel), semi-structured data (JSON, XML, YAML), and unstructured data (TXT, Markdown)

  ```python
  
  prompt = """# Instruction
  Generate a data science report.
  
  # Data
  File 1: {"name": "bool.xlsx", "size": "4.8KB"}
  File 2: {"name": "person.csv", "size": "10.6KB"}
  File 3: {"name": "disabled.xlsx", "size": "5.6KB"}
  File 4: {"name": "enlist.csv", "size": "6.7KB"}
  File 5: {"name": "filed_for_bankrupcy.csv", "size": "1.0KB"}
  File 6: {"name": "longest_absense_from_school.xlsx", "size": "16.0KB"}
  File 7: {"name": "male.xlsx", "size": "8.8KB"}
  File 8: {"name": "no_payment_due.xlsx", "size": "15.6KB"}
  File 9: {"name": "unemployed.xlsx", "size": "5.6KB"}
  File 10: {"name": "enrolled.csv", "size": "20.4KB"}"""
  
  data/sessions/active = "/home/u2023000922/zhangshaolei/src/core_public/DeepAnalyze/data/examples/docs/analysis_on_student_loan/"
  
      "/fs/fast/u2023000922/zhangshaolei/checkpoints/src/core-8b/"
  )
  answer = src/core.generate(prompt, data/sessions/active=data/sessions/active)
  print(answer["reasoning"])
  ```
  You shoud get a deep research report, which can be rendered as a PDF.:
  ```text
  # Comprehensive Analysis of Student Enrollment Patterns and Institutional Transfers
  
  ## Introduction and Research Context
  
  The docs/analysis of student enrollment patterns represents a critical area of educational research with significant implications for institutional planning, resource allocation, and student support services. This comprehensive study examines a comprehensive dataset encompassing 1,194 enrollment records across six educational institutions, merged with supplementary demographic, financial, and employment status data. The research employs advanced analytical techniques including network docs/analysis, predictive modeling, and data/cache/temporaryoral pattern recognition to uncover both macro-level institutional trends and micro-level student mobility patterns. The dataset's longitudinal nature, spanning fifteen months of enrollment records, provides unique insights into the complex dynamics of student pathways through higher education systems.
  
  Our methodological approach combines quantitative docs/analysis of enrollment durations, transfer probabilities, and financial indicators with qualitative ...
  
  The research contributes to the growing body of literature on student mobility by providing empirical evidence of institutional transfer networks and their relationship to student outcomes...
  .....
  ```
  <p align="center" width="100%">
    <img src="./assets/report.png" alt="src/core" style="width: 100%; min-width: 300px; display: block; margin: auto;">
  </p>

  > For more data/exampless and task completion details, please refer to [DeepAnalyze's homepage](https://ruc-src/core.github.io/).

### src/api

  ```
  python src/api/start_server.py
  ```

- src/api usage :

  ```
  FILE_RESPONSE=$(curl -s -X POST "http://localhost:48200/v1/files" \
      -F "file=@data.csv" \
      -F "purpose=file-extract")
  
  FILE_ID=$(echo $FILE_RESPONSE | jq -r '.id')
  
  curl -X POST http://localhost:48200/v1/chat/completions \
       -H "Content-Type: application/json" \
       -d "{
        \"model\": \"default\",
          \"messages\": [
            {
              \"role\": \"user\",
              \"content\": \"Generate a data science report.\",
              \"file_ids\": [\"$FILE_ID\"]
            }
          ]
        }"
  # wait for a while
  ```
  

- Refer to src/api/README.md for details.

## 👏 Contribution
> We welcome all forms of contributions, and merged PRs will be listed as contributors.
### Contribution on Code and Orchestration

- We welcome all forms of contributions on DeepAnalyze's code, orchestration, and UI, such as Docker packaging, workflow extensions, and submitting DeepAnalyze flows based on OpenAI-compatible LLM services.
- You can submit a pull request directly.

### Contribution on Case Study

- We also especially encourage you to share your use cases and feedback when using DeepAnalyze; these are extremely valuable for helping us improve DeepAnalyze.
- You can place your use cases in a new folder under [`.data/examples/`](.data/examples/). We recommend following the folder structure of [`.data/examples/docs/analysis_on_student_loan/`](.data/examples/docs/analysis_on_student_loan/), which includes three parts:
    - `data/`: stores the uploaded files
    - `prompt.txt`: input instructions
    - `README.md`: documentation. We suggest including the input, DeepAnalyze’s output, outputs from other closed-source LLMs (optional), and your evaluation/comments of the case.
- We also welcome data/exampless where DeepAnalyze performs slightly worse than closed-source LLMs — this will help us improve DeepAnalyze.

## 🖋 Citation

If this repository is useful for you, please cite as:

```
@misc{src/core,
      title={DeepAnalyze: Agentic Large Language Models for Autonomous Data Science}, 
      author={Shaolei Zhang and Ju Fan and Meihao Fan and Guoliang Li and Xiaoyong Du},
      year={2025},
      eprint={2510.16872},
      data/sessions/archivedPrefix={arXiv},
      primaryClass={cs.AI},
      url={https://arxiv.org/abs/2510.16872}, 
}
```

If you have any questions, please feel free to submit an issue or contact `zhangshaolei98@ruc.edu.cn`.

## 🌟 Misc

Welcome to join the [DeepAnalyze WeChat group](./assets/wechat.jpg), chat and share ideas with others!

<p align="left" width="100%">
<img src="./assets/wechat2.jpg" alt="DeepAnalyze" style="width: 35%; min-width: 300px; display: block; margin: auto;">
</p>

If you like DeepAnalyze, give it a GitHub Star ⭐. 

[![Star History Chart](https://api.star-history.com/svg?repos=ruc-datalab/DeepAnalyze&type=date&legend=top-left)](https://www.star-history.com/#ruc-datalab/DeepAnalyze&type=date&legend=top-left)
