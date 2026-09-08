# Claude Study Companion：VS Code、Claude API 与 GitHub 完整操作

这份指南只列你本人需要完成的动作。项目代码、测试、配置、README 和 GitHub Actions
已经准备好；你负责使用自己的账号授权、填入 API key、实际试用和最后决定是否公开。

## 一、在 VS Code 打开项目

1. 解压项目。
2. 打开 VS Code。
3. 选择 **File → Open Folder**，打开 `claude-study-companion`，不要只打开 `app.py`。
4. 若 VS Code 显示 Recommended Extensions，选择安装。主要是 Python、Ruff 和 Markdown。

## 二、建立 Python 环境

在 VS Code 选择 **Terminal → New Terminal**，确认终端路径位于项目文件夹，然后运行：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
```

如果电脑没有 Python 3.12，可以先运行 `py --list`，再把第一行的 `3.12` 改成已经安装的
3.10、3.11 或 3.13。

然后按 `Ctrl+Shift+P`，输入 **Python: Select Interpreter**，选择项目里的
`.venv\Scripts\python.exe`。

## 三、安全设置 Claude API key

1. 在 Anthropic Console 创建 API key。
2. 在终端运行：

```powershell
Copy-Item .streamlit\secrets.toml.example .streamlit\secrets.toml
```

3. 打开新产生的 `.streamlit/secrets.toml`。
4. 只替换 `replace_with_your_key`，保留双引号。
5. 保存文件，但不要发送给别人，也不要截图。

真实的 `secrets.toml` 已经被 `.gitignore` 排除。你可以用以下命令确认：

```powershell
git check-ignore .streamlit/secrets.toml
```

它应该输出 `.streamlit/secrets.toml`。如果没有输出，先不要 commit。

## 四、运行项目

```powershell
.\.venv\Scripts\python -m streamlit run app.py
```

浏览器通常会自动打开 `http://localhost:8501`。也可以在 VS Code 左边打开
**Run and Debug**，选择 **Streamlit: Claude Study Companion**，然后按绿色按钮。

先点 **Use demo notes**，再依序测试四种模式。自动测试不会调用 API，但这里的实际生成
会消耗少量 Claude API credits。

## 五、运行免费自动测试

```powershell
.\.venv\Scripts\python -m pytest
.\.venv\Scripts\python -m ruff check .
.\.venv\Scripts\python -m compileall -q app.py src tests
```

三个命令都应成功。详细人工测试见 `docs/TESTING_CHECKLIST.md`。

## 六、建立 GitHub repository

1. 登录 GitHub，选择 **New repository**。
2. Repository name 填 `claude-study-companion`。
3. Description 可填：

   `A responsible Claude-powered study companion for lecture notes, practice, explanations, and Socratic learning.`

4. 先选择 Public 或 Private。若是申请作品集，测试完成后再设 Public 比较稳妥。
5. 不要勾选自动加入 README、`.gitignore` 或 License，因为项目里已经有。
6. 创建后复制 GitHub 给你的 HTTPS repository URL。

回到 VS Code Terminal：

```powershell
git init
git add .
git status
git commit -m "Build Claude Study Companion MVP"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/claude-study-companion.git
git push -u origin main
```

把 URL 中的 `YOUR_USERNAME` 改成你的 GitHub username。执行 `git status` 时再次确认看不到
`.streamlit/secrets.toml`。

如果 GitHub 要求登录，请在浏览器完成 Git Credential Manager 授权；不要把 GitHub 密码或
Claude API key 贴进聊天或写进命令。

## 七、公开 demo 的最终决定

最安全的一天版公开 demo 是 BYOK：部署时不要设置服务器的 `ANTHROPIC_API_KEY`，访客必须
在 password field 输入自己的 key。这样别人不会消耗你的 API balance。

如果你想让评审打开就能用自己的服务器 key：

- 先把 app 设为 private 或只给指定评审；
- 在部署平台的 Secrets 页面加入 key；
- 不要把 key 放入 GitHub；
- 明白目前的每-session 12 次限制可以通过新 session 绕过，它不等于真正的全局 quota。

等你确认作品内容、API 成本和访问对象后，再决定 Public + BYOK，还是 Private + server key。

## 你需要亲自完成的最终清单

- [ ] 创建或确认 Claude API key 有可用 credits
- [ ] 在本机建立 `.streamlit/secrets.toml`
- [ ] 运行自动测试
- [ ] 用自己的 lecture notes 测试四种模式
- [ ] 判断回答质量并告诉 Codex 要调整的 prompt/UI
- [ ] 创建 GitHub repository 并完成账号授权 push
- [ ] 检查 GitHub 页面没有任何 key
- [ ] 决定 repository Public / Private
- [ ] 决定 demo 使用 BYOK / 私有 server key / 暂不部署
- [ ] 若要申请 Campus Ambassador，录制约两分钟 demo
