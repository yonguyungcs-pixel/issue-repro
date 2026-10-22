[English](README.md) · [简体中文](README.zh-CN.md) · **繁體中文** · [日本語](README.ja.md)

# issue-repro

`issue-repro` 用來準備一份別人跑得起來的 GitHub issue 重現材料。它會寫出一個小目錄，裡面有腳本、環境說明，以及預期結果和實際結果。確認腳本能重現問題之後，用 `pack` 壓成 zip，附到 issue 上。

需要 Python 3.10 或更新版本。執行時只用標準函式庫。

## 安裝

在這個儲存庫裡：

```bash
pip install -e .
issue-repro --version
```

安裝後可以得到 `issue-repro` 命令。目前版本是 `0.1.0`。

## 命令

### init

寫一份空白的 `repro/` 範本：

```bash
issue-repro init
```

- `README.md`：摘要、步驟、執行方式
- `environment.md`：作業系統、Python 版本，以及其他環境資訊
- `requirements.txt`：需要固定版本的套件
- `repro.py`：盡量小的重現腳本。改寫之前，它以結束代碼 1 離開
- `EXPECTED.txt`：預期發生的事
- `ACTUAL.txt`：實際發生的事

`--dir` 可以換成別的目錄名稱。`--force` 會覆寫這些範本檔，你另外放進目錄的檔案會保留。

### from-issue

用一則 GitHub issue 填寫同一套範本：

```bash
issue-repro from-issue OWNER/REPO#123
issue-repro from-issue https://github.com/OWNER/REPO/issues/123
```

標題寫入摘要，內文寫入步驟。公開 issue 不需要 token。如果設定了 `GITHUB_TOKEN` 或 `GH_TOKEN`，命令會把它放進 `Authorization` 請求標頭。token 只出現在請求標頭裡，不會寫進目錄或 zip。

如果請求失敗，命令仍會寫下空白範本，並把錯誤記在 `repro/README.md` 開頭。

### pack

```bash
issue-repro pack
```

在目前目錄產生 `issue-repro-<slug>.zip`。目錄來自某則 issue 時，slug 是 `owner-repo-123`；否則用專案目錄名稱。`-o path.zip` 用來指定輸出路徑。壓縮檔裡包含 `repro/` 目錄。

## 範例

```bash
issue-repro from-issue pallets/flask#1
# 編輯 repro/repro.py，讓問題還在時腳本失敗
python repro/repro.py
issue-repro pack
```

產生的檔案是 `issue-repro-pallets-flask-1.zip`。可以把它附在 issue 上，也可以留在本機。

## 擷圖

下面是這個版本實際跑出來的終端機紀錄。

`issue-repro --version` 和 `issue-repro --help`：

![issue-repro 的版本和說明](docs/screenshots/help.png)

`issue-repro init` 以及產生的 `repro/` 檔案（`repro.py` 結束代碼為 1）：

![issue-repro init 和目錄清單](docs/screenshots/init.png)

對公開 issue `pallets/flask#1` 執行 `from-issue` 之後的 README：

![從 Flask 的公開 issue 填寫範本](docs/screenshots/from-issue.png)

`issue-repro pack` 產生的 zip：

![issue-repro pack 產生 zip](docs/screenshots/pack.png)

## 開發

```bash
pip install -e ".[dev]"
ruff check .
pytest
```

見 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 授權

[MIT](LICENSE)
