# A-Closure 构建与测试记录摘要

以下状态来自冻结 attempt index（SHA-256 `e4e798bcd01bc81b45749fbb042a0ef9894215921b5270ab86b87aa0c5dee5f3`）及所列原始日志；index 未公开是因为其中含本机路径，批准公开的输入哈希已列入 `run_config.json`。对应日志的路径脱敏公开副本在本目录，见 `build.*`、`python-tests.*` 和 `rust-*.{stdout,stderr}`；原始与公开副本的哈希/字节数列于 `manifest.json`。未公开源码、二进制、资产、DB 内容或完整上游源码。

| 项目 | 结果 | 原始日志（相对 ignored `evidence/server_build_20261017/`） |
|---|---|---|
| Full workspace server CLI build，locked，nightly-2025-09-08，plugins feature | exit 0；Cargo `Finished dev`，报告 2m42s。binary SHA-256 `c578dfb4b72347e64025969b0c42753e68402d883e5e23941d970712aadd877d` | stderr 1,650 B，SHA-256 `955e663774f422aa24451ecacf5b7d966dd7575073c0eaece02679e1bece1ee2`；stdout 0 B，空文件 SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| Python harness/CLI tests | 15 passed, 0 failed；1.030 s | stderr 2,462 B，SHA-256 `fa9b03edac7ac2c3fe00fe1e0c01045b60207995ef71fab862ccfa605a8b4b7a`；stdout 0 B，空文件 SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `veloren-common` focused test | 1 passed, 0 failed | stdout 234 B，SHA-256 `17a227d16578a09ea48f819541a383f84804e39f8caac511eabff7cf5cad3b5d`；stderr 437 B，SHA-256 `8b0449739b8781dcf7d5d05cb104782182090031b927b4b7ab2eb9fdb31bc1c1` |
| `veloren-rtsim` focused tests | 8 passed, 0 failed | stdout 1,717 B，SHA-256 `cd563a2f8971655f067b015849c6fa07776835817cc48b176ca491e99de34837`；stderr 1,319 B，SHA-256 `bb23e6ef32b345d166481d073910309eed7c02bb1c10f90dbd84d807121c17cb` |
| `veloren-server` focused tests | 5 passed, 0 failed | stdout 1,080 B，SHA-256 `c423b5da0fa55733a5ebbab3e4efd078786290092f6b3f042d56706f9c969f46`；stderr 7,622 B，SHA-256 `3af5185486c94cc9b2a35076ffa8ae71a24cc70cd7b1dae0301de820fc4e58aa` |

另有一次非规范 target-dir 选择的构建尝试，父级确认退出码 130，分类为构建目标配置失误而非编译失败。其已保存 stderr 为 5,384 B，SHA-256 `d1ac3a75576b6e2a7382f3574a221b1dcd9afac747ff391c26ea627bd3b99efa`；stdout 为空。公开的 `wrong-target-build.*` 是对应日志副本；stderr 没有 compiler error 结论，也未发现认证材料。另一次临时目录权限预检只留下工具输出，没有独立原始日志文件；它不是编译尝试。随后 canonical target build exit 0，详细日志见上表。

Rust test subtotal is 14/14. Older failed build/test attempts remain in historical build evidence and are not represented as passes here. Original Cargo.lock remained unchanged. The build/tests establish compilation and focused test status only, not native interaction success.
