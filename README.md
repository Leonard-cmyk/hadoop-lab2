# Hadoop 文档倒排索引

使用 Java MapReduce 对十篇公开英文技术文档建立词频倒排索引。

当前验证状态：下载脚本已实际下载十篇文档，Shell/Python 语法检查通过。
Hadoop 编译与 YARN 集成测试尚待在 Linux 虚拟机登录后执行，暂不作为已验证提交版。

## 环境与运行

Linux、JDK 11、Hadoop 3.4.2（HDFS + YARN）、Python 3。Python 脚本只用标准库。
先启动已有 Hadoop 集群，不要格式化 NameNode。实验零环境可以执行：

```bash
source ~/hadoop-lab/env.sh
bash ~/hadoop-lab/start.sh
python3 scripts/download_docs.py
bash scripts/run.sh
python3 tests/integration.py
```

`build.sh` 使用 Hadoop 自带依赖编译，不需要 Maven。
`scripts/run.sh` 每次生成独立的 HDFS 输入、配置及输出目录，不覆盖之前的实验。
本地结果在 `results/`，`results/latest.txt` 记录主作业运行目录。

## 数据来源与预处理

下载 https://docs.python.org/3.11/tutorial/ 下的十篇英文文档：

| 文件 | 网页 | 内容 |
|---|---|---|
| document01.txt | introduction.html | Python 入门 |
| document02.txt | controlflow.html | 控制流 |
| document03.txt | datastructures.html | 数据结构 |
| document04.txt | modules.html | 模块 |
| document05.txt | inputoutput.html | 输入与输出 |
| document06.txt | errors.html | 错误与异常 |
| document07.txt | classes.html | 类 |
| document08.txt | stdlib.html | 标准库概览 |
| document09.txt | stdlib2.html | 标准库概览二 |
| document10.txt | venv.html | 虚拟环境与包 |

下载器提取网页正文区域，保留正文、示例代码和正文标题，排除侧栏和导航。
`data/manifest.json` 保存完整 URL、下载时间、字节数及 SHA-256。
网页正文及其原始 HTML 仅在本地保留，不随仓库发布；其版权归原作者。

统一转换为小写，以 `[a-z]+` 提取英文词，数字、标点、下划线作为分隔符。
例如 `Python-python` 得到两个 `python`；`can't` 分成 `can` 与 `t`，都被停词表过滤。
不做词干还原、不合并单复数。`stopwords.txt` 是本实验手工定义的通用英文停词表，
同时保留程序领域词；它并不是唯一或通用最优的停词表。

输入采用平面目录，每个 `.txt` 文件名必须唯一，并只含英文字母、数字、点、横线或下划线。
文档 ID 来自 FileSplit 的文件名，同一文件拆成多个输入分片时仍合并到同一 ID。

## 核心算法

1. Mapper 加载分布式缓存中的停词表；每个保留词输出 `(word, document\t1)`。
2. Combiner 在本地按文档累计次数，保持值格式为 `document\tcount`。
3. Shuffle 按词分组；Reducer 用 TreeMap 汇总各文档次数，按文件名排序，计算总词频。
4. 使用一个 Reducer，使输出词条全局按字典序排列。

输出示意（仅说明格式，不是实际语料统计）：

```text
data	<document01.txt,6>;<document02.txt,3>;<total,9>.
```

词与列表之间为制表符；列表最后有句点；空文件和仅停词文件不产生词条。
Combiner 可不执行或执行多次，均不影响正确性；不能把格式化最终结果的 Reducer
直接当作 Combiner。

## 验证

`tests/verify.py` 独立用 Python 串行统计全部输入，与 MapReduce 的全部词条及
全部文档计数逐项比较，同时检查总次数、停词过滤、词条/文档排序与输出格式。

```bash
python3 tests/verify.py data/input results/<运行编号>/index.txt stopwords.txt
```

`tests/integration.py` 在 YARN 上运行六份人工边界文档，覆盖大小写、标点、
跨行重复、数字、空文件、全停词文件、同一文档多个输入分片。
分别启用和禁用 Combiner，核对两个输出字节一致，并与独立参考结果比较。
`RAW_TOKENS`、`STOP_TOKENS`、`KEPT_TOKENS`、`UNIQUE_WORDS` 是主作业自定义计数器。

## 限制

这是小规模教学实现。一个词的文档列表在 Reducer 内存中聚合，单 Reducer 也限制了并行度。
大规模语料需要复合键/二次排序、多 Reducer 和分片索引等设计。
文件名作为 ID 的前提是输入目录内唯一；不支持递归目录中的同名文件。
停词表会过滤 `if` 等代码关键词，这符合通用文本检索设定，但不适合精确代码检索。

## 参考

- Python 官方教程：https://docs.python.org/3.11/tutorial/
- Hadoop MapReduce 教程：https://hadoop.apache.org/docs/r3.4.2/hadoop-mapreduce-client/hadoop-mapreduce-client-core/MapReduceTutorial.html
- Hadoop HDFS Shell：https://hadoop.apache.org/docs/r3.4.2/hadoop-project-dist/hadoop-common/FileSystemShell.html
