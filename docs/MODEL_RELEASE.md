# 模型附件下载与恢复

当前模型快照：[models-2026-09-29](https://github.com/asmellperson/vision-lab/releases/tag/models-2026-09-29)。

源码保存在 Git 仓库；22 套模型分别打包为 `vision-lab-model-<id>.tar.gz`。为提高当前上传连接的稳定性，大于 16 MiB 的压缩包拆成 `.tar.gz.part-001`、`.part-002` 等分卷，较小的压缩包直接上传。所有附件都在同一个 Release 中。包内路径为 `models/<id>/...`，应在项目根目录解压。

## 附件内容

- 各模型的原始权重、配置、词表和已有模型卡片。
- 原始 `inventory.json`，保留来源、版本和文件 SHA256；打包前已逐个校验。
- `models/<id>/release-metadata/` 下的来源说明、上游仓库许可全文及许可文件来源记录。上游代码许可与模型卡片分别保留，不对第三方材料重新授予许可。
- `model-release-manifest.json`：22 个完整压缩包、各自分卷的大小与 SHA256，以及完整包内文件清单。
- `SHA256SUMS`：实际下载附件（含每个分卷、发布清单和说明）的校验值。
- `ARCHIVE_SHA256SUMS`：合并后 22 个完整压缩包的校验值。
- `RESTORE.md`：本说明的独立副本，可随离线附件一起保存。

下载缓存、锁文件、运行数据和依赖不包含在附件中。`models/resnet18/resnet18.onnx` 是可重新生成的推理缓存，也不包含在快照中。校验值用于验证完整性，不是上游签名。

## 下载全部模型

需要已安装并按仓库访问要求登录 GitHub CLI（`gh`），以及 `tar`、`sha256sum`。在新克隆且尚未下载模型的项目根目录执行：

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

分卷或完整包校验失败都会停止解压；`--keep-old-files` 遇到已有同名文件会报错并停止，避免覆盖本机模型。已有部分模型时，建议先在另一份新克隆的项目中恢复快照，再按需使用。下载目录会保留，可作为离线备份；分卷、合并包和解压后的模型合计需要约 13 GiB，建议预留至少 15 GiB 空间。

也可在 Release 页面手动下载附件。恢复单套模型时，下载该模型的完整压缩包或全部分卷，以及两个校验清单。在下载目录先验证已下载附件：

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

## 恢复后启动

模型附件不包含 Python/Node.js 依赖。新机器仍需按 [README](../README.md#在新机器安装) 安装环境；模型已经恢复后，可跳过 `scripts/download_models.py --all`，直接启动：

```bash
bash scripts/start.sh
```

后续也可以继续使用 `scripts/download_models.py` 从官方来源下载模型。模型任务与许可标签见 [MODELS.md](MODELS.md)，各模型的实际原始文件清单保存在附件里的 `inventory.json`。
