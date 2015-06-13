Title: Swap 函数的坑
Date: 2015-06-13
Modified:2015-06-13
Category: 日志
Tags: C++，
Slug:swap-trap
Author: 杨海祥


昨天在刷 Leetcode　的时候，掉进一个坑里面了，害得自己调了快一个小时，在此记录一下。

在交换两个变量的值的时候，用一个中间变量总感觉比较　Low，所以就学着大神们使用异或运算来完成这事儿，所以我写了如下这么一段代码(C++)，最后果然装逼失败：

```
[1]    void swap(int &a, int &b) {
[2]        a = a ^ b;
[3]        b = a ^ b;
[4]        a = a ^ b;
[5]    }
```

大神看到这段代码可能立马就知道我这个小白错误在哪儿了，如果没有怎么用过这种方法交换变量的值，那么可能没有看出来问题在哪儿。先解释以下这几句代码。

其实非常的简单，可以看成如下：

```
b = (a^b)^b = a;
a = (a^b)^a = b;
```

这代码很简单啊，没什么错啊，我当时就是这样想的。但是等到我使用它的时候，调试过程中发现了神奇的一幕。就 a,b 两个值相等（至少我当时认为是相等）时，a 和 b 就都变成了 0。难道相等交换后不应该相等吗？难道这个算法有问题，我自己仔细手算了一遍。发现没问题啊，即使 a b 值相等了，最终结果也应该是对的啊,简单没天理了。  

中间经历过各种猜测后，我最终决定单步输出,看一下这个磨人的小妖精到底在哪儿。所以，我在第2，3，4 步之前都打结果输出出来。结果发现执行完第二步后，a,b 都变成了 0。当时我就懵逼了，真 TM 神奇，难道编译器有问题啊。天啦，我竟然发现 g++ 编译器有问题。果然，大神们是不会出问题的，问题只可能出现在自己的身上。  

我去仔细看了一下汇编代码，发现在取变量的值的时候，两个变量的地址值竟然是相同的，此刻我才幡然醒悟。原来 a,b 引用的是同一个变量，所以一异或后，两个变量全都变成了 0， 那后面无论如何都得不到正确的结果了。p.s 我是用 swap 交换数组变量的值，所以没发现 swap 的同一个变量。幸好，最后还是发现了问题出在哪儿，吃一堑长一智,所以正确的代码可以这样写：  

```
[1]    void swap(int &a, int &b) {
[2]		   if (a == b) return;
[3]        a = a ^ b;
[4]        b = a ^ b;
[5]        a = a ^ b;
[6]    }
``` 

不知道有没有更漂亮的代码。