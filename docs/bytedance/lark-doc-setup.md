# 飞书文档 Skills 配置指南

> **注意**：本功能仅适用于字节跳动内部的 TRAE Agent，用于操作飞书（Lark）文档。
> skill 文件可以随本仓库一起通过 Git 管理，但认证信息仍然必须保留在本地，不进入远程仓库。

## 概述

`lark-doc` skill 是飞书官方提供的 AI Agent skill，用于通过自然语言操作飞书云文档，包括：
- 读取、总结、提取文档内容
- 创建、编辑、修改文档
- 插入、下载文档中的图片和附件
- 操作画板、电子表格等富文本元素

## 目录结构

```
.agents/skills/
├── lark-doc/          # 飞书文档操作 skill
└── lark-shared/       # 飞书共享配置（认证、权限等）
```

本地凭证目录：

```text
.lark-cli/             # 本地认证与配置，必须继续 gitignore
```

## 安装步骤

### 1. 安装 lark-cli

#### Linux / macOS

```bash
npm config set prefix "$HOME/.npm-global"
export PATH="$HOME/.npm-global/bin:$PATH"
npm install -g @larksuite/cli

# 验证安装
lark-cli --version
```

如果希望 PATH 持久生效，再把下面这一行写入 `~/.bashrc` 或 `~/.zshrc`：

```bash
export PATH="$HOME/.npm-global/bin:$PATH"
```

#### Windows PowerShell

```powershell
$NpmGlobal = Join-Path $HOME ".npm-global"
New-Item -ItemType Directory -Force -Path $NpmGlobal | Out-Null
npm config set prefix $NpmGlobal
$env:Path = "$NpmGlobal;$env:Path"
npm install -g @larksuite/cli
lark-cli --version
```

如果希望对后续终端持久生效，可以把 `$HOME\.npm-global` 加到用户级 PATH。

### 2. 获取 lark-doc 和 lark-shared skills

优先级如下：

1. **直接使用当前仓库内已存在的 skill 文件**
   如果你是通过 `git clone` 获取本仓库，通常已经包含：
   - `.agents/skills/lark-doc/`
   - `.agents/skills/lark-shared/`
2. **如果当前环境缺少这些目录，再从官方来源补齐**

```bash
# 在仓库根目录执行
test -f .agents/skills/lark-doc/SKILL.md
test -f .agents/skills/lark-shared/SKILL.md
```

如果缺失，可以再执行：

```bash
npx -y skills add larksuite/cli --skill lark-doc
```

然后检查文件是否回到 `.agents/skills/` 下。

### 3. 创建飞书应用

1. 访问 [飞书开放平台](https://open.feishu.cn/)
2. 登录你的飞书账号
3. 创建**企业自建应用**：
   - 应用名称：例如 "TRAE 飞书助手"
   - 应用描述：用于 TRAE AI Agent 操作飞书文档
4. 获取凭证：
   - 进入应用 → "凭证与基础信息"
   - 记录 **App ID**（类似 `cli_xxxxxxxxxxxxxx`）
   - 记录 **App Secret**（点击"查看"获取，类似 `secret_xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`）
5. 开通权限：
   - 进入"权限管理"
   - 搜索并开通以下权限（至少需要）：
     - `doc:document:readonly` - 查看文档
     - `doc:document` - 编辑文档
     - `drive:drive:readonly` - 查看云空间
     - `drive:drive` - 编辑云空间
   - 点击"批量申请"或逐个申请权限
6. 发布应用：
   - 进入"版本发布与调试"
   - 创建版本 → 保存 → 申请发布
   - 等待企业管理员审批
   - （测试用）可以在"设置" → "测试企业"中添加自己为测试人员，无需审批

### 4. 配置应用凭证

```bash
# 方式一：通过 stdin 安全输入 App Secret
echo "your-app-secret" | lark-cli config init --app-id your-app-id --app-secret-stdin

# 方式二：交互式配置
lark-cli config init --app-id your-app-id
# 按提示输入 App Secret

# 验证配置
lark-cli config show
```

说明：

- `.lark-cli/` 目录包含本地认证和配置，不应提交到 Git
- 这意味着你切换到 Windows 本地 TRAE / IDE 环境后，需要在 Windows 本机重新完成认证
- 这是预期行为，因为 skill 文件可以跨平台走 Git，而凭证必须留在各自机器本地

### 5. OAuth 用户授权

```bash
# 发起授权请求（split-flow 方式，推荐）
lark-cli auth login --domain docs,drive --no-wait --json

# 从输出中提取 verification_url 和 device_code
# 生成二维码
lark-cli auth qrcode "verification_url" --output ./lark-auth-qrcode.png

# 扫描二维码或打开链接完成授权
# 完成后执行：
lark-cli auth login --device-code "your-device-code"

# 验证授权状态
lark-cli auth status
```

## 使用方式

配置完成后，可以直接用自然语言操作飞书文档：

### 读取文档
```
帮我读取这个飞书文档：https://bytedance.larkoffice.com/docx/xxxxx
总结一下这个文档的要点：[文档链接]
提取文档中关于"部署"的内容
```

### 创建文档
```
帮我创建一个新的飞书文档，标题是"项目周报"，内容包括...
把这段文字整理成飞书文档
```

### 编辑文档
```
帮我在文档末尾追加一段内容：[文档链接]
把文档中的"张三"改成"李四"：[文档链接]
帮我在这个章节后面插入一个表格：[文档链接]
```

### 媒体操作
```
帮我下载文档里的图片：[文档链接]
帮我把这张截图插入到文档末尾：[文档链接]
```

## 常用命令

```bash
# 读取文档
lark-cli docs +fetch --api-version v2 --doc "文档URL或token"
lark-cli docs +fetch --api-version v2 --doc "doc-token" --doc-format markdown

# 创建文档
lark-cli docs +create --api-version v2 --content '<title>标题</title><p>内容</p>'

# 编辑文档
lark-cli docs +update --api-version v2 --doc "doc-token" --command append --content '<p>追加内容</p>'
lark-cli docs +update --api-version v2 --doc "doc-token" --command str_replace --pattern "旧内容" --content "新内容"

# 查看授权状态
lark-cli auth status

# 重新授权
lark-cli auth login --domain docs,drive
```

## 注意事项

1. **安全**：
   - 不要将 App Secret 提交到代码仓库
   - `.lark-cli/` 目录已在 `.gitignore` 中排除
   - 不要在终端明文输出 App Secret 或 Access Token

2. **权限**：
   - Bot 身份无法访问用户的个人文档（日历、云空间等）
   - 需要访问用户资源时，必须使用 User 身份进行 OAuth 授权
   - 遇到权限错误时，检查是否在飞书开放平台开通了对应的 scope

3. **Token 有效期**：
   - Access Token 有效期约 2 小时
   - Refresh Token 有效期约 7 天
   - 过期后会自动刷新，无需手动操作

4. **高风险操作**：
   - 删除、覆盖等操作会先向用户确认
   - 可以使用 `--dry-run` 预览操作效果

5. **跨平台**：
   - skill 文件走 Git：`.agents/skills/lark-doc/`、`.agents/skills/lark-shared/`
   - 本地认证不走 Git：`.lark-cli/`
   - Windows / macOS / Linux 都可以直接使用同一份仓库，只需要分别在本机安装 `lark-cli` 并完成认证

## 故障排查

### 问题：找不到应用
- 确认是否在飞书开放平台创建了企业自建应用
- 确认应用是否已发布并获得审批
- 确认是否添加了测试人员（测试环境）

### 问题：权限不足
- 检查 `lark-cli auth status` 中的 scope 列表
- 在飞书开放平台"权限管理"中申请缺失的权限
- 重新执行 OAuth 授权：`lark-cli auth login --scope "missing_scope"`

### 问题：命令执行失败
- 检查网络连接是否正常
- 检查 App ID 和 App Secret 是否正确
- 查看错误信息中的 `hint` 字段，按提示操作
- 执行 `lark-cli update` 更新到最新版本

### 问题：切到 Windows 本地环境后不能直接访问飞书
- 确认 Windows 本机已经安装 `lark-cli`
- 确认 Windows 本机重新完成了 `config init` 和 `auth login`
- 确认 agent 读取的是当前仓库中的 `.agents/skills/lark-doc/SKILL.md`

## 参考链接

- [飞书开放平台](https://open.feishu.cn/)
- [lark-cli GitHub 仓库](https://github.com/larksuite/cli)
- [飞书文档 API 文档](https://open.feishu.cn/document/server-docs/docs/docs-overview)
