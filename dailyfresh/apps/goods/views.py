from django.shortcuts import render,redirect
from django.views.generic import View
from goods.models import GoodsCategory, Goods, GoodsSKU, IndexGoodsBanner, IndexPromotionBanner, IndexCategoryGoodsBanner
from django.core.cache import cache
from django_redis import get_redis_connection
from django.core.urlresolvers import reverse
from django.core.paginator import Paginator, EmptyPage
import json
# Create your views here.


class BaseCartView(View):
    """提供购物车数据统计功能"""
    def get_cart_num(self, request):
        cart_num = 0

        # do something
        # 如果用户登陆，就从redis中获取购物车数据
        if request.user.is_authenticated():
            # 创建redis_conn对象
            redis_conn = get_redis_connection('default')
            # 获取用户id
            user_id = request.user.id
            # 从redis中获取购物车数据，返回字典，如果没有数据，返回None，所以不需要异常判断
            cart = redis_conn.hgetall('cart_%s'%user_id)
            # 遍历购物车字典，累加购物车的值
            for value in cart.values():
                cart_num += int(value)
        else:
            # 如果用户未登录，就从cookis中获取购物车数据
            cart_json = request.COOKIES.get('cart') # json字符串
            # 判断购物车数据是否存在
            if cart_json is not None:
                # 将json字符串购物车数据转换成json字典
                cart_dict = json.loads(cart_json)
            else:
                cart_dict = {}
            # 遍历购物车字典，计算商品数量
            for val in cart_dict.values():
                cart_num += val
        return cart_num


class ListView(BaseCartView):
    """商品列表"""

    def get(self, request, category_id, page_num):

        # 获取sort参数:如果用户不传，就是默认的排序规则
        sort = request.GET.get('sort', 'default')

        # 校验参数
        # 判断category_id是否正确，通过异常来判断
        try:
            category = GoodsCategory.objects.get(id=category_id)
        except GoodsCategory.DoesNotExist:
            return redirect(reverse('goods:index'))

        # 查询商品所有类别
        categorys = GoodsCategory.objects.all()

        # 查询该类别商品新品推荐
        new_skus = GoodsSKU.objects.filter(category=category).order_by('-create_time')[:2]

        # 查询该类别所有商品SKU信息：按照排序规则来查询
        if sort == 'price':
            # 按照价格由低到高
            skus = GoodsSKU.objects.filter(category=category).order_by('price')
        elif sort == 'hot':
            # 按照销量由高到低
            skus = GoodsSKU.objects.filter(category=category).order_by('-sales')
        else:
            skus = GoodsSKU.objects.filter(category=category)
            # 无论用户是否传入或者传入其他的排序规则，我在这里都重置成'default'
            sort = 'default'

        # 分页：需要知道从第几页展示
        page_num = int(page_num)

        # 创建分页器：每页两条记录
        paginator = Paginator(skus, 10)

        # 校验page_num：只有知道分页对对象，才能知道page_num是否正确
        try:
            page_skus = paginator.page(page_num)
        except EmptyPage:
            # 如果page_num不正确，默认给用户第一页数据
            page_skus = paginator.page(1)

        # 获取页数列表
        page_list = paginator.page_range

        # 购物车
        cart_num = self.get_cart_num(request)
        # 构造上下文
        context = {
            'sort':sort,
            'category':category,
            'cart_num':cart_num,
            'categorys':categorys,
            'new_skus':new_skus,
            'page_skus':page_skus,
            'page_list':page_list,
        }

        # 渲染模板
        return render(request, 'list.html', context)


class DetailView(BaseCartView):
    """商品详细信息页面"""

    def get(self, request, sku_id):

        # 尝试获取缓存数据
        context = cache.get("detail_%s" % sku_id)

        # 如果缓存不存在
        if context is None:
            try:
                # 获取商品信息
                sku = GoodsSKU.objects.get(id=sku_id)
            except GoodsSKU.DoesNotExist:
                # from django.http import Http404
                # raise Http404("商品不存在!")
                return redirect(reverse("goods:index"))

            # 获取类别
            categorys = GoodsCategory.objects.all()

            # 从订单中获取评论信息
            sku_orders = sku.ordergoods_set.all().order_by('-create_time')[:30]
            if sku_orders:
                for sku_order in sku_orders:
                    sku_order.ctime = sku_order.create_time.strftime('%Y-%m-%d %H:%M:%S')
                    sku_order.username = sku_order.order.user.username
            else:
                sku_orders = []

            # 获取最新推荐
            new_skus = GoodsSKU.objects.filter(category=sku.category).order_by("-create_time")[:2]

            # 获取其他规格的商品
            other_skus = sku.goods.goodssku_set.exclude(id=sku_id)

            context = {
                "categorys": categorys,
                "sku": sku,
                "orders": sku_orders,
                "new_skus": new_skus,
                "other_skus": other_skus
            }

            # 设置缓存
            cache.set("detail_%s" % sku_id, context, 3600)
        # 购物车数量
        cart_num = self.get_cart_num(request)
        # 如果是登录的用户
        if request.user.is_authenticated():
            #
            user_id = request.user.id
            # 从redis中获取购物车信息
            redis_conn = get_redis_connection("default")
            #  如果redis中不存在，会返回None

            # 浏览记录: lpush history_userid sku_1, sku_2
            # 移除已经存在的本商品浏览记录
            redis_conn.lrem("history_%s" % user_id, 0, sku_id)
            # 添加新的浏览记录
            redis_conn.lpush("history_%s" % user_id, sku_id)
            # 只保存最多5条记录
            redis_conn.ltrim("history_%s" % user_id, 0, 4)
        context.update({"cart_num": cart_num})

        return render(request, 'detail.html', context)


class IndexView(BaseCartView):
    """主页"""

    def get(self, request):
        """查询首页需要的数据， 构造上下文，并渲染"""

        # 先从缓存中读取数据，如果有就获取缓存数据，反之，就执行查询
        context = cache.get('index_page_data')
        if context is None:
            # 查询用户公个人信息(request.user)
            # 查询数据商品数据
            # 查询商品分类
            categorys = GoodsCategory.objects.all()
            # 查询图片轮播信息:按照index进行排序
            banners = IndexGoodsBanner.objects.all().order_by('index')
            # 查询活动信息
            promotion_banners = IndexPromotionBanner.objects.all().order_by('index')
            # 查询分类商品
            for category in categorys:
                title_banners = IndexCategoryGoodsBanner.objects.filter(category=category, display_type=0).order_by('index')
                category.title_banners = title_banners
                image_banners = IndexCategoryGoodsBanner.objects.filter(category=category, display_type=1).order_by('index')
                category.image_banners = image_banners

            # 构造上下文

            context ={
                'categorys': categorys,
                'banners': banners,
                'promotion_banners': promotion_banners,
            }
            # 设置缓存数据：名字，内容，有效期
            cache.set('index_page_data', context, 3600)
        # 查询购物车信息
        cart_num = self.get_cart_num(request)
        # 补充购物车数据
        context.update(cart_num=cart_num)
        return render(request, 'index.html', context)


