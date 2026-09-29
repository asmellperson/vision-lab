# 模型下载与安装

模型发布版本：[models-2026-09-29](https://github.com/asmellperson/vision-lab/releases/tag/models-2026-09-29)。

源码仓库不包含模型权重。Release 提供 22 套模型，每套对应 `vision-lab-model-<id>.tar.gz`。部分模型采用 `.tar.gz.part-001`、`.part-002` 等分卷格式，需下载该模型的全部分卷并按编号合并。包内路径为 `models/<id>/...`，解压位置为项目根目录。

## 附件内容

- 各模型的原始权重、配置、词表和已有模型卡片。
- `inventory.json`：模型来源、版本及各文件的 SHA256。
- `models/<id>/release-metadata/` 下的来源说明、上游仓库许可全文及许可文件来源记录。上游代码许可与模型卡片分别保留，不对第三方材料重新授予许可。
- `model-release-manifest.json`：22 个完整压缩包、各自分卷的大小与 SHA256，以及完整包内文件清单。
- `SHA256SUMS`：实际下载附件（含每个分卷、发布清单和说明）的校验值。
- `ARCHIVE_SHA256SUMS`：合并后 22 个完整压缩包的校验值。
- `RESTORE.md`：可随附件保存的离线安装说明。

下载缓存、锁文件、运行数据和依赖不包含在附件中。`models/resnet18/resnet18.onnx` 是可重新生成的推理缓存，也不包含在快照中。校验值用于验证完整性，不是上游签名。

## 下载全部模型

以下命令使用 Bash、GitHub CLI（`gh`）、`tar` 和 `sha256sum`。如 `gh` 提示需要认证，先完成 `gh auth login`。在项目根目录执行，目标模型目录应为空：

```bash
(
  set -eu
  snapshot_dir="$(mktemp -d)"
  echo "模型附件下载目录：$snapshot_dir"
  gh release download models-2026-09-29 \
    --repo asmellperson/vision-lab \
    --pattern 'vision-lab-model-*.tar.gz*' \
    --pattern model-release-manifest.json \
    --pattern SHA256SUMS \
    --pattern ARCHIVE_SHA256SUMS \
    --pattern RESTORE.md \
    --dir "$snapshot_dir"
  (cd "$snapshot_dir" && sha256sum --check SHA256SUMS)
  for first in "$snapshot_dir"/*.tar.gz.part-001; do
    [ -f "$first" ] || continue
    archive="${first%.part-001}"
    cat "$archive".part-* > "$archive"
  done
  (cd "$snapshot_dir" && sha256sum --check ARCHIVE_SHA256SUMS)
  for archive in "$snapshot_dir"/vision-lab-model-*.tar.gz; do
    tar --extract --gzip --file "$archive" --directory . --keep-old-files
  done
)
```

分卷或完整包校验失败时，脚本会停止，不执行后续解压。`--keep-old-files` 遇到同名文件会报错并保留已有文件。已有部分模型时，可先解压到空目录，再按需复制缺少的模型。下载目录会保留，可作为离线备份；分卷、合并包和解压后的模型合计需要约 13 GiB，建议预留至少 15 GiB 空间。

## 下载单个模型

可在 Release 页面手动下载目标模型的完整压缩包或全部分卷，以及 `SHA256SUMS`、`ARCHIVE_SHA256SUMS`。在下载目录先验证已下载附件：

```bash
sha256sum --check --ignore-missing SHA256SUMS
```

确认目标附件显示 `OK` 后，对分卷模型执行合并（例如 `resnet18`），然后核对完整包：

```bash
cat vision-lab-model-resnet18.tar.gz.part-* > vision-lab-model-resnet18.tar.gz
sha256sum --check --ignore-missing ARCHIVE_SHA256SUMS
```

未分卷的小模型无需执行 `cat`。确认完整包显示 `OK` 后，解压到项目根目录，例如：

```bash
tar --extract --gzip --file vision-lab-model-resnet18.tar.gz \
  --directory /path/to/vision-lab --keep-old-files
```

## 安装后启动

模型附件不包含 Python/Node.js 依赖，需先按 [README](../README.md#安装与启动) 安装运行环境。安装模型后，在项目根目录启动：

```bash
bash scripts/start.sh
```

后续也可以继续使用 `scripts/download_models.py` 从官方来源下载模型。模型任务与许可标签见 [MODELS.md](MODELS.md)，各模型的实际原始文件清单保存在附件里的 `inventory.json`。
