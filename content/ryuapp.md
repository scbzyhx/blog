Title: Ryu 源码分析之 RyuApp
Date: 2015-07-27
Modified:2015-07-27
Category: 日志
Tags: SDN, Ryu, OpenFlow
Slug: ryu_ryuapp
Author: 杨海祥

本篇博客是 Ryu 源码分析的第一篇，前段时间用 Ryu 时由于需要去看了一下其源代码，因此对其有一定了解。在此，将其记录下来。  Ryu 是一个 python 实现的 SDN 控制器，其目前支持到 OpenFlow 1.3 版本。同时还支持 OVSDB， netconf 协议 。更多的内容可以参考官网[文档](http://osrg.github.io/ryu/)。  

# 核心对象 RyuApp

每一个学习的 Ryu 的用户，接触到的第一个东西就是 app_manager.RyuApp 类。因为你实现一个应用时，手册都会告诉你需要去继承这个类，然后再实现一些方法等等。由此也可见，这其实是一个 Ryu 中一个非常核心的概念。它到底是什么呢？简单来说，默认情况下每一个 RyuApp 实例（为了方便，我们将 RyuApp 子类的实例也称之为 RyuApp 的实例，下同）对应一个 greenlet 线程 (这是一种非常轻量级的用户态线程)。如果你自己额外创建新的线程则会存在一个 RyuApp 实例有多个线程的情况。而这些线程的上下文，即运行环境，就是这个这个 RyuApp 对象了。也就是说，一个应用会对应一个 RyuApp 实例，一个线程。其中实例提供上下文环境，而这个线程对应的函数就是 RyuApp 的 _event_loop 函数（稍后会分析）。  

# 启动过程概要

如果你用过 set_ev_cls 就会明白，线程之间或者说应用之间通过事件进行通信，那么这些事件到底是怎么进行路由的呢，即如何放到各 RyuApp 实现的事件队列中的呢，如何建立这种联系呢（至少写代码的时候不太容易明白），就需要先大致了解一下怎么么启动的了。启动的详细过程，在后面的博客会详解，这儿只说个大概内容。  

其实，所有的多线程应用都是从单线程开始的， Ryu 也不例外。 使用 ryu-manger app.py 启动应用后，  

1.  主线程先通过 app.py 获得所依赖的所有其它类（您应该已经知道了，可通过 _CONTEXTS 获得）。  
2.  再创建所有这些类的对象并初始化，并将对象保存起来，创建对象字典。  
3.  接下来用该字典初始化 app.py 中的的应用。  
4.  将所有的对象都创建完毕后，建立对象这些对象之间的联系，比如 A 接收 B 发送的事件，则 A B 之前必然需要某些机制来关联起来。这种关联就是在这个阶段完成的。  
5.  最后，再启动各对象对应的线程。然后整个应用就启动起来了。  

其实这里面最难理解的应该就属于如何建立这些线程之间复杂的关系了。 要想了解这个复杂的关联，我们需要分析一下 RyuApp 的源代码，下面我将对比着源代码来说明这个过程。  

# RyuApp 源代码剖析  

```
class RyuApp(object):

    _CONTEXTS = {}

   """
   前面已经说了，_CONTEXTS 就是解决依赖的。所有位于在 _CONTEXTS 类都会相应的生成一个对象。将这些对象建立一个类似于 _CONTEXTS 的字典，只是将这个对象字典中的值由类换成了相应的类的实例。而这个实例字典会用于初始化本实例。
   例如：
          _CONTEXTS = {
            'network': network.Network
        }
        def __init__(self, *args, *kwargs):
            self.network = kwargs['network']
    会生成一个 Network 类的实例。而 kwargs 实则为 {"network":Netwok_instance}
   """
    _EVENTS = []
    """
    这个列表存放，本类会产生的事件的类。如果这个类会产生 A 类事件，则将该事件放到 _EVENTS 中。
   这样做的目的在于，如果一个类 Receiver 对这个事件 A 感兴趣，在建立联系的阶段（上面说的第4阶段）主线程就依据 _EVENTS 将 Receiver 的实例注册到本实例中。 这个过程在启动过程中可以看到。 
    """

    OFP_VERSIONS = None
    """
    本应用支持的 OpenFlow 版本号，在启动阶段会用到。默认支持所有版本。
    """

    @classmethod
    def context_iteritems(cls):
        """
        Return iterator over the (key, contxt class) of application context
        """
        return iter(cls._CONTEXTS.items())
    """
    前面说到， _CONTEXTS 解决应用依赖的问题，这个类方法用于获得 _CONTEXTS
    """

    def __init__(self, *_args, **_kwargs):
        super(RyuApp, self).__init__()
        self.name = self.__class__.__name__    #本应用的名称，是全局唯一的，可以通过名称来查找实例。如果你想直接调用实现的方法时，可以这么干。
        
        self.event_handlers = {}        # ev_cls -> handlers:list  # 事件处理函数字典，事件类到处理函数的映射。 _event_loop 中对每个事件都从这个数据结构中查找相应的处理函数并调用。
        self.observers = {}     # ev_cls -> observer-name -> states:set  #这个对应存储哪些实例会对本实例的产生的事件感兴趣，则相应的存储于此 observers 中。

        #前面的个数据结构就解决了应用之间相互关联的问题， 如果 A 对应 B 的某个事件感兴趣，则 B 就会出现在 A 的 observers 中，而 B 中处理事件的函数则在 B 自己的 event_handler 中。

        self.threads = []     #存储本应用启动的 greenlet 线程，默认情况下只有 _event_loop 对应的线程。当然可以另外启动线程。 
        self.events = hub.Queue(128)  #这个对列存放发送至本实例的所有事件。
        if hasattr(self.__class__, 'LOGGER_NAME'):  # 日志记录
            self.logger = logging.getLogger(self.__class__.LOGGER_NAME)
        else:
            self.logger = logging.getLogger(self.name)
        self.CONF = cfg.CONF  # 全局配置，

        # prevent accidental creation of instances of this class outside RyuApp
        class _EventThreadStop(event.EventBase):   #这个事件内部使用，用于通知线程终止。在 stop 方法中会用到。
            pass
        self._event_stop = _EventThreadStop()
        self.is_active = True    # 标识线程是否结束。

    def start(self):  ##此函数启动线程， 可以看到对应的函数为 _event_loop，这个函数不停地处理到达的事件。
        """
        Hook that is called after startup initialization is done.
        """
        self.threads.append(hub.spawn(self._event_loop))

    def stop(self):
        self.is_active = False
        self._send_event(self._event_stop, None)
        hub.joinall(self.threads)
   """
   结束线程，可以看到首先将，is_active 设置为 false, 再发送一个结束事件。 
   """

    def register_handler(self, ev_cls, handler):
        assert callable(handler)
        self.event_handlers.setdefault(ev_cls, [])
        self.event_handlers[ev_cls].append(handler)
   """
   注册事件处理器，handler 即注册的处理函数（对其进行了一些包装）。_event_loop 线程根据这个 event_handler 字典处理到达的事件。
   """

    def unregister_handler(self, ev_cls, handler):
        assert callable(handler)
        self.event_handlers[ev_cls].remove(handler)
        if not self.event_handlers[ev_cls]:
            del self.event_handlers[ev_cls]
    """
    取消注册
    """

    def register_observer(self, ev_cls, name, states=None):
        states = states or set()
        ev_cls_observers = self.observers.setdefault(ev_cls, {})
        ev_cls_observers.setdefault(name, set()).update(states)
    
    """
    这个函数用于声明告诉本应用，其它某些应用对本应用产生的某些事件感兴趣。在此处注册后，本应用产生事件时，就会将事件消息发送至那些感兴趣的应用的事件队列中。
    """
    def unregister_observer(self, ev_cls, name):
        observers = self.observers.get(ev_cls, {})
        observers.pop(name)

    def unregister_observer_all_event(self, name):
        for observers in self.observers.values():
            observers.pop(name, None)

    def observe_event(self, ev_cls, states=None):
        brick = _lookup_service_brick_by_ev_cls(ev_cls)
        if brick is not None:
            brick.register_observer(ev_cls, self.name, states)
    """
    如果本应用对某个事件感兴趣，那么就可以调用这个函数将其注册到产生该事件的应用中。
    其中 _lookup_service_brick_by_ev_cls 函数会在全局 SERVICE_BRICKS 数组中查找产生指定事件消息的应用。
    SERVICE_BRICKS 数组存储了启动的所有的应用。
    """
    def unobserve_event(self, ev_cls):
        brick = _lookup_service_brick_by_ev_cls(ev_cls)
        if brick is not None:
            brick.unregister_observer(ev_cls, self.name)

    def get_handlers(self, ev, state=None):
        """Returns a list of handlers for the specific event.
        :param ev: The event to handle.
        :param state: The current state. ("dispatcher")
                      If None is given, returns all handlers for the event.
                      Otherwise, returns only handlers that are interested
                      in the specified state.
                      The default is None.
        """
        ev_cls = ev.__class__
        handlers = self.event_handlers.get(ev_cls, [])
        if state is None:
            return handlers

        def test(h):
            if not hasattr(h, 'callers') or ev_cls not in h.callers:
                # dynamically registered handlers does not have
                # h.callers element for the event.
                return True
            states = h.callers[ev_cls].dispatchers
            if not states:
                # empty states means all states
                return True
            return state in states

        return filter(test, handlers)
    """
    查找并返回事件的处理函数
    """
    def get_observers(self, ev, state):
        observers = []
        for k, v in self.observers.get(ev.__class__, {}).items():
            if not state or not v or state in v:
                observers.append(k)

        return observers
    """
    返回对指定事件（本应用产生的）感兴趣的其它应用。
    """

    def send_request(self, req):
        """
        Make a synchronous request.
        Set req.sync to True, send it to a Ryu application specified by
        req.dst, and block until receiving a reply.
        Returns the received reply.
        The argument should be an instance of EventRequestBase.
        """

        assert isinstance(req, EventRequestBase)
        req.sync = True
        req.reply_q = hub.Queue()
        self.send_event(req.dst, req)
        # going to sleep for the reply
        return req.reply_q.get()
    """
    同步发送请求。它将请求发送到 req.dst 指定的应用，并阻塞到收到返回。其它它本质也是用事件消息实现的，不过它主动睡眠，等待被处理后（reply_q 中有了数据），再从 get 函数的阻塞处继续执行。
   """
    def _event_loop(self):
        while self.is_active or not self.events.empty():
            ev, state = self.events.get()
            if ev == self._event_stop:
                continue
            handlers = self.get_handlers(ev, state)
            for handler in handlers:
                handler(ev)
    """
    应用线程的主体部分。其非常简单。即不停地从队列中取出事件消息，将查找相应的处理函数，再调用算出函数。
    """
    def _send_event(self, ev, state):
        self.events.put((ev, state))
    
    """
    向自己的队列中发送事件消息，停止消息应该用到了它。
    """
    def send_event(self, name, ev, state=None):
        """
        Send the specified event to the RyuApp instance specified by name.
        """

        if name in SERVICE_BRICKS:
            if isinstance(ev, EventRequestBase):
                ev.src = self.name
            LOG.debug("EVENT %s->%s %s",
                      self.name, name, ev.__class__.__name__)
            SERVICE_BRICKS[name]._send_event(ev, state)
        else:
            LOG.debug("EVENT LOST %s->%s %s",
                      self.name, name, ev.__class__.__name__)
    """
    向指定的应用（name）发送事件消息。应用由名称指定，应用的实例从全局变量 SERVICE_BRICK 查找所得，然后直接将消息发送到该应用的消息队列中。
    """       

    def send_event_to_observers(self, ev, state=None):
        """
        Send the specified event to all observers of this RyuApp.
        """

        for observer in self.get_observers(ev, state):
            self.send_event(observer, ev, state)
    """
    将事件消息发送到那些对其感兴趣的应用的队列中。所谓的感兴趣，即指调用 register_observer 注册过的应用。
    """
    def reply_to_request(self, req, rep):
        """
        Send a reply for a synchronous request sent by send_request.
        The first argument should be an instance of EventRequestBase.
        The second argument should be an instance of EventReplyBase.
        """

        assert isinstance(req, EventRequestBase)
        assert isinstance(rep, EventReplyBase)
        rep.dst = req.src
        if req.sync:
            req.reply_q.put(rep)
        else:
            self.send_event(rep.dst, rep)
    """
    处理同步请求，往reply_q 队列中放入数据即可唤醒 send_reqeust。
    """

    def close(self):
        """
        teardown method.
        The method name, close, is chosen for python context manager
        """
        pass
    """
    本来应该是打算终止本线程的，不过不知道为什么根本没有用到。目前 Ryu 的终止还是相当的粗暴，只能直接使用 Ctrl+C。
    """
``` 

上面就是 RyuApp 类的代码部分了。所有应用之间的交互过程其实也不是太复杂，如果 A 应用产生事件 a，而 B 应用对事件 a 感兴趣，希望 A 产生该事件的时候，通知B。那么 B 在初始化时就会使用 register\_observer 在 A 处注册，以告诉 A，B 对 A 的 a 事件感兴趣，那么 A 产生该事件消息时，就会调用 send\_event\_to\_observer 将 a 放到 B 的消息队列中。 B 中再处理消息并调用相应的消息处理函数就 OK 了。这样就实现了各应用之间的通信了。

那么还剩下两个问题了：

1. 我们从来没有调用  register\_observer 去显式注册，那么这种注册到底是什么时候完成的呢？
2. 我们并没有使用 register\_handler 注册一个事件消息处理函数，那么这个又是什么时候完成的呢？

这两个问题与应用加载的过程十分密切，所以我们需留在下一篇博客解释初始化过程的时候再来讲解。

预告：消息处理函数的注册与 set\_ev\_cls 与 set\_ev\_handler 有十分密切的关系。
