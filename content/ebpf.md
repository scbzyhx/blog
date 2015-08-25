Title: eBPF
Date: 2015-08-25
Modified:2015-08-25
Category: 日志
Tags: nfv, 
Slug: ebpf
Author: 杨海祥

几天前，Linux 基金会成立了一个新的项目 Iovisor。其目标为实现灵活的数据平面，加速 nfv。其基本技术为 eBPF，即 extensible Berkeley Packet Filter。 其基本思路是使用一种灵活的方式在内核实现对网络数据包的处理，而不需要像传统的方法那样通过加载内核模块的方式来实现、或者通过繁重的系统调用在用户态算不 。接下来我们会讲一下什么是 eBPF，从其诞生到发展开始讲起。  

##BPF

eBPF 起源为 [BPF](https://zh.wikipedia.org/wiki/BPF)，它提供一种内核的数据包过滤机制。它的基本机制是在内核提供一个虚拟机，用户态将过滤规则以虚拟机指令的形式传递到内核，由内核根据这些指令来过滤网络数据包。1997 年 BPF 被引入到 linux 2.1.75 版本中（由于后面的 eBPF，现在其也被称之为 cBPF，即 classic BPF）。 cBPF 虚拟机提供了两个32位寄存器，30 条指令（store, load, arithmetic,branch,return,transfer）、10 种寻址模式、16 个 32 位寄存器（内存映射）。程序一般生成一个 bool 值，保留或者丢弃数据包。如果想更多了解 BPF 的细节，可以参考论文 [The BSD Packet Filter: A New Architecture for User-level Packet Capture](http://www.tcpdump.org/papers/bpf-usenix93.pdf)。

使用 BPF 的接口为 setsockopt。参数为 SO\_ATTCH\_FILTER。指令以数组的方式传递到内核中。

这种在内核态机制处理数据包的方法可以避免数据从内核到用户态的拷贝，以提高数据的处理速度，但是可能令人担心的是虚拟机的速率。为了提高 BPF，JIT 对其进行了加速。  

## JIT  

2011 年时， JIT 被加入到内核以加速 BPF 程序的执行速度。不过，它只是支持 x86\_64 系统结构。其思路也是非常的简单，即是尽量将寄存器直接映射为 x86\_64 的物理寄存器，将虚拟机指令也尽可能直接地映射机器指令。更多内容可参考：[https://lwn.net/Articles/437981](https://lwn.net/Articles/437981)。  

## eBPF

Linux 3.15 开始引入 eBPF。其扩充了 BPF 的功能，丰富了[指令集](https://www.kernel.org/doc/Documentation/networking/filter.txt)。

- 10 个 64 位寄存器。
- 支持函数调用
- 指令数增加至 90 条
- 所有的指令都在 64 位模式。
- ABI 调用规范：
	- R0 寄存器：返回值（或程序的返回值）
	- R1-R5 寄存器：参数
	- R6-F9 寄存器：被调用者保存的寄存器
	- R10 寄存器：只读帧指针。
- 增加了 Map ，可以在内核保存数据
- 新增加了 bpf() 系统调用
- 等等。

可见，cBPF, JIT 严格算来都不能算作虚拟机，因为它们甚至都不能使用函数调用。而到了 eBPF 后，虚拟机的功能并都更加强大，使得我们对数据包的操作都可以在内核灵活地实现，完全不需要加载重新编译，而且可以在线替换等，灵活性大大增加。数据平面也就变得更加灵活（可以随时改变对每个数据包的处理行为）。

虽然说到的都是对于网络数据包的处理，但是 eBPF 目前已并只处理网络包了，其总共四个方面：  

- BPF\_PROG\_TYPE\_SOCK\_FILTER
- BPF\_PROG\_TYPE\_KPROBE
- BPF\_PROG\_TYPE\_SCHED\_CLS
- BPF\_PROG\_TYPE\_SOCK\_ACT

另外三类功能到底是什么可以参考相关的文献。  

可见，这种虚拟机的机制使得要想改变对网络数据包的处理行为变得非常灵活而且在内核中完成该功能使得性能大大提高（避免从内核到用户态的拷贝）。当然，其安全性等问题也还是非常地重要的，毕竟内核几乎就有了绝对的权限。此内容以后再说。   
