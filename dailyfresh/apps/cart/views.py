from django.shortcuts import render
from django.http import JsonResponse
from django.views.generic import View
from goods.models import GoodsSKU
from django_redis import get_redis_connection

import json
# Create your views here.


class CartInfoView(View):
    """获取购物车数据"""
    def get(self,request):
        """提供购物车页面；不需要请求参数"""
        # 查询购物车数据
        # 如果用户登录从redis中获取数据
        if request.user.is_authenticated():
            # 创建redis连接对象
            # 获取所有数据
            pass
        else:
            pass

        # 保存编历出来的sku
        sku = []
        # 总金额
        # 总数量

        # 编历cart_dict,形成模版所需要的数据
        # 构造上下文
        context = {
            
        }
        return render(request, 'cart.html', context)




class AddCartView(View):
    """添加购物车"""

    def post(self, request):

        # 判断用户是否登陆
        # if not request.user.is_authenticated():
        #     return JsonResponse({'code': 1, 'message':'用户未登录'})

        # 接收数据：user_id，sku_id，count
        user_id = request.user.id
        sku_id = request.POST.get('sku_id')
        count = request.POST.get('count')
        # 校验参数all()
        if not all([sku_id, count]):
            return JsonResponse({'code': 2, 'message': '参数不完整'})

        # 判断商品是否存在
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'code': 3, 'message': '商品不存在'})
        # 判断count是否是整数
        try:
            count = int(count)
        except Exception:
            return JsonResponse({'code': 4, 'message': '数量错误'})

        # 判断库存
        # if count > sku.stock:
            # return JsonResponse({'code': 5, 'message': '库存不足'})

        # 提示：无论是否登陆状态，都需要获取suk_id,count,校验参数。。。
        # 所以等待参数校验结束后，再来判断用户是否登陆
        # 如果用户已登录，就保存购物车数据到redis中
        if request.user.is_authenticated():
            # 用户id
            user_id = request.user.id
            # 操作redis数据库存储商品到购物车
            redis_conn = get_redis_connection('default')
            # 需要先获取添加到购物车的商品是否存在
            origin_count = redis_conn.hget('cart_%s'%user_id, sku_id)
            # 如果商品在购物车中存在，就直接累加商品数量；反之,把新的商品和数量添加到购物车
            if origin_count is not None:
                count += int(origin_count)
            # 判断库存:计算最终的count与库存比较
            if count > sku.stock:
                return JsonResponse({'code': 5, 'message': '库存不足'})

            # 储存到redis
            redis_conn.hset('cart_%s' % user_id, sku_id, count)
            # 为了配合模板中js交互并展示购物车的数量，在这里需要查询一下购物车的总数
            cart_num = 0
            cart_dict = redis_conn.hgetall('cart_%s' % user_id)
            for val in cart_dict.values():
                cart_num += int(val)
            # json方式响应添加购物车结果
            return JsonResponse({'code': 0, 'message': '添加购物车成功', 'cart_num': cart_num})
        else:
            # 如果用户未登录，就保存购物车数据到cookie中
            # 先从cookie的购物车信息中，获取当前商品的记录,json字符串购物车数据
            cart_json = request.COOKIES.get('cart')

            # 判断购物车cookie数据是否存在，有可能用户从来没有操作过购物车
            if cart_json is not None:
                # 将json字符串转成json字典
                cart_dict = json.loads(cart_json)
            else:
                # 如果用户没有操作购物车，就给个空字典
                cart_dict = {}

            if sku_id in cart_dict:
                # 如果cookie中有这个商品记录，则直接进行求和；如果cookie中没有这个商品记录，则将记录设置到购物车cookie中
                origin_count = cart_dict[sku_id]
                count += origin_count

            # 判断库存：计算最终的count与库存比较
            if count > sku.stock:
                return JsonResponse({'code': 6, 'message': '库存不足'})

            # 设置最终的商品数量到购物车
            cart_dict[sku_id] = count

            # 计算购物车总数
            cart_num = 0
            for val in cart_dict.values():
                cart_num += val

            # 将json字典转成json字符串
            cart_str = json.dumps(cart_dict)

            # 将购物车数据写入到cookie中
            response = JsonResponse({"code": 0, "message": "添加购物车成功", 'cart_num': cart_num})
            response.set_cookie('cart', cart_str)
            return response

