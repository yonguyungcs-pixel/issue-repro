[English](README.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · **日本語**

# issue-repro

`issue-repro` は、GitHub issue を他の人が実行できる小さなフォルダにまとめます。中には再現スクリプト、環境メモ、期待する結果と実際の結果が入ります。スクリプトで問題を再現できたら、`pack` で zip にして issue に添付します。

Python 3.10 以降が必要です。実行時の依存は標準ライブラリだけです。

## インストール

このリポジトリで:

```bash
pip install -e .
issue-repro --version
```

インストールすると `issue-repro` コマンドが使えます。現在のバージョンは `0.1.0` です。

## コマンド

### init

空の `repro/` テンプレートを書きます。

```bash
issue-repro init
```

- `README.md`: 要約、手順、実行方法
- `environment.md`: OS、Python のバージョン、その他の環境
- `requirements.txt`: バージョンを固定したいパッケージ
- `repro.py`: 問題を示す最小のスクリプト。書き換えるまでは終了コード 1 です
- `EXPECTED.txt`: 期待する結果
- `ACTUAL.txt`: 実際の結果

`--dir` でフォルダ名を変えられます。`--force` はテンプレートのファイルだけを置き換え、あとから追加したファイルはそのまま残します。

### from-issue

GitHub issue の内容で同じテンプレートを埋めます。

```bash
issue-repro from-issue OWNER/REPO#123
issue-repro from-issue https://github.com/OWNER/REPO/issues/123
```

タイトルは要約に、本文は手順になります。公開 issue には token は要りません。`GITHUB_TOKEN` または `GH_TOKEN` がある場合は、`Authorization` ヘッダとして送ります。token はヘッダだけに使い、フォルダや zip には書きません。

取得に失敗しても空のテンプレートは作成し、エラーを `repro/README.md` の先頭に残します。

### pack

```bash
issue-repro pack
```

カレントディレクトリに `issue-repro-<slug>.zip` を作ります。issue から作ったフォルダなら slug は `owner-repo-123`、そうでなければプロジェクトのディレクトリ名です。`-o path.zip` で出力先を指定できます。zip の中には `repro/` ディレクトリが入ります。

## 例

```bash
issue-repro from-issue pallets/flask#1
# 問題が残っているあいだ失敗するよう repro/repro.py を編集する
python repro/repro.py
issue-repro pack
```

できるファイルは `issue-repro-pallets-flask-1.zip` です。issue に添付するか、手元に残します。

## スクリーンショット

このバージョンのコマンドを実際に実行した端末です。

`issue-repro --version` と `issue-repro --help`:

![issue-repro のバージョンとヘルプ](docs/screenshots/help.png)

`issue-repro init` とできた `repro/` の一覧（`repro.py` の終了コードは 1）:

![issue-repro init とファイル一覧](docs/screenshots/init.png)

公開 issue `pallets/flask#1` に対する `from-issue` と、書き出された README:

![Flask の公開 issue からテンプレートを埋めた結果](docs/screenshots/from-issue.png)

`issue-repro pack` が作った zip:

![issue-repro pack の結果](docs/screenshots/pack.png)

## 開発

```bash
pip install -e ".[dev]"
ruff check .
pytest
```

[CONTRIBUTING.md](CONTRIBUTING.md) を参照してください。

## ライセンス

[MIT](LICENSE)
