# 本地协作写入锁：仅迁移交接或准备写入时读取

writer.py 在工作目录保存持久所有权记录，用操作系统文件锁串行化修改记录。遵守本技能的对话在每次写入批次前 assert；它无法阻止绕过协议的编辑器/进程，也不是分布式锁。只用于同一主机的本地文件系统。

所有命令用绝对 workspace 和可识别 owner ID。claim JSON 是令牌凭据，保存在任务 work/ 等本地目录、位于迁移包外；只传精确路径，不公开令牌。执行脚本无需加载源码。

1. 源端进入协议：`python <skill>/scripts/writer.py acquire <workspace> --owner <source-id> --claim <source-claim.json>`
2. 每次写入批次前：`python <skill>/scripts/writer.py assert <workspace> --claim <claim.json>`
3. 交接前完成所有在途写入，STATE 记 quiesced，固定 task_id/snapshot_id 并核对账本与实际状态；源端不再启动写入批次。
4. 原子转交到唯一 handoff ID（不依赖尚未生成的新对话 ID）：`python <skill>/scripts/writer.py transfer <workspace> --claim <source-claim.json> --owner <handoff-id> --new-claim <receiver-claim.json> --snapshot-id <task-id/revision-id>`
5. receiver-claim 的精确本地路径仅交给一个接收端。接收端通过回执、现场及停写检查后执行：`python <skill>/scripts/writer.py assert <workspace> --claim <receiver-claim.json> --snapshot-id <task-id/revision-id>`，成功才写入。旧 claim 已失效，不能广播新 claim 给多个对话。
6. 无待续写工作且操作完成后：`python <skill>/scripts/writer.py release <workspace> --claim <claim.json>`

普通 active checkpoint 不转交所有权。旧包没有锁时先取得停写证据，无持有者才能 acquire；必须确认旧源端不会继续写入。

不自动因超时夺锁。崩溃或 claim 丢失时用 status 查看 owner，检查真实进程/对话并恢复原 claim。无法确认停写就 DEFER。人工恢复先停稳全部写入并保留原状态，不能把时间流逝当作停写证据。

transfer 报错时以 assert 为准；已生成但未生效的 claim 不可写入。创建对话失败而锁已转交时，确认接收端未运行后，用 receiver claim 再 transfer 回源端并生成新 claim；不得复用旧令牌。
