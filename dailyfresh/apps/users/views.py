from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.views.generic import View
# 反向解析
from django.core.urlresolvers import reverse
from users.models import User, Address
from django import db
from celery_tasks.tasks import send_active_email
import re
from django.conf import settings
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import SignatureExpired
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from utils.views import LoginRequiredMixin
from django_redis import get_redis_connection
# Create your views here.


class UserInfoView(LoginRequiredMixin, View):
    """用户中心"""
    def get(self, request):
        """查询用户信息和地址信息"""
        # 从request中获取user对象,中间件从验证请求中的用户,所以request中带由user
        user = request.user
        try:
            # 查询用户地址,根据创建时间排序,取第1个地址
            address = user.address_set.latest('create_time')
        except Address.DoesNotExist:
            # 如果地址信息不存在
            address = None

        # 构造上下文
        context = {
            'address': address
        }
        # 渲染模板
        return render(request, 'user_center_info.html', context)
        # 创建redis连接对象
        redis_connection = get_redis_connection('default')
        # 从Redis中获取用户浏览商品的sku_id，在redis中需要维护商品浏览顺序[8,2,5]
        sku_ids = redis_connection.lranage('histtory_%s'% user.id, 0, 4)
        # 从数据库查询sku信息,范围在sku_ids中
        # skuList = GoodsSKU.object.filter(id__in=sku_ids)
        # 问题,经过数据库查询后得到skuList, 就不再是redis中维护的顺序了,而是[2,5,8]
        # 需求: 保证经过数据库查询后,依然是[8,2,5]
        skuList = []
        for sku_id in sku_ids:
            sku = GoodsSKU.objects.get(id=sku_id)
            skuList.append(sku)
        # 构造上下文
        context = {
            'address': address,
            'skuList':skuList,
        }
        # 调出并渲染模板
        return render(request, 'user_center_info.html', context)



class AddressView(LoginRequiredMixin, View):
    """用户地址"""
    def get(self, request):
        """提供用户地址页面"""
        # 或取登陆用户
        user = request.user
        # 查询数据
        try:
            address = user.address_set.latest('create_time')
        except Address.DoesNotExist:
            address = None
        # 构造上下文
        context = {
            'address': address
        }
        # 渲染模板
        return render(request, 'user_center_site.html', context)

    def post(self, request):
        """修改地址信息"""
        # 接受编辑的地址参数
        user = request.user
        recv_name = request.POST.get('recv_name')
        addr = request.POST.get('addr')
        zip_code = request.POST.get('zip_code')
        recv_mobile = request.POST.get('recv_mobile')
        # 校验地址参数
        if all([recv_name, addr, zip_code, recv_mobile]):
            # 保存地址参数
            Address.objects.create(
                user=user,
                receiver_name=recv_name,
                detail_addr=addr,
                zip_code=zip_code,
                receiver_mobile=recv_mobile,
            )

        # 响应结果
        return redirect(reverse('users:address'))


class LogoutView(View):
    """退出登陆"""
    def get(self, request):
        """处理退出登陆的逻辑"""
        # 由django用户认证系统完成, 需要清理cook和 session, request参数中有user对象
        logout(request)
        # 退出跳转, 由产品经理设计
        return redirect(reverse('goods: index'))


class LoginView(View):
    """登陆"""
    def get(self, request):
        """提供登陆页面"""
        return render(request, 'login.html')

    def post(self, request):
        """处理登陆逻辑"""
        # 接收请求参数
        user_name = request.POST.get('user_name')
        pwd = request.POST.get('pwd')
        # 获取是否勾选'记住用户名'
        remembered = request.POST.get('remembered')
        # 验校请求参数
        if not all([user_name, pwd]):
            return redirect(reverse('users:login'))
        # 判断用户是否存在
        user = authenticate(username=user_name, password=pwd)
        if user is None:
            # 提示用户名或密码错误

            return render(request, 'login.html', {'errmsg': '用户名或密码错误'})
        # 判断用户是否是激活用户
        if not user.is_active:
            return render(request, 'login.html', {'errmsg': '请激活'})
        # 登入该用户
        login(request, user)

        # 判断是否是否勾选'记住用户名'
        if remembered != 'on':
            # 没有勾选，不需要记住cookie信息，浏览会话结束后过期
            request.session.set_expiry(60*60*24*10)
        else:
            # 已勾选，需要记住cookie信息，两周后过期
            request.session.set_expiry(None)
        # 跳转到主页
        # 登陆成功，根据next参数决定跳转方向
        next = request.GET.get('next')
        if next is None:
            # 如果是直接登陆成功，就重定向到首页
            pass
            # return redirect(reverse('goods:index'))
        else:
            # 如果是用户中心重定向到登陆页面，就回到用户中心
            return redirect(next)


class ActiveView(View):
    """邮件激活"""
    def get(self, request, token):
        """处理激活请求"""
        # 创建虚拟化器: 注意<调用loads方法的序列化器的参数要和调用dumps方法时的参数一致>
        serializer = Serializer(settings.SECRET_KEY, 3600)
        try:
            # 解出原始字典{'confirm': self.id}
            result = serializer.loads(token)
        except SignatureExpired:
            return HttpResponse('激活连接已经去过期')
        # 获取user
        user_id = result.get('confirm')
        try:
            # 查询user
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return HttpResponse('用户不存在')

        # 重置激活状态为Ture
        user.is_active = True
        # 手动保存一次
        user.save()

        # 相应结果
        return redirect(reverse('users:login'))


class RegisterView(View):
    """提供注册页面和登陆逻辑"""

    def get(self, request):
        """提供注册页面"""
        return render(request, "register.html")

    def post(self, request):
        """处理注册逻辑,储存注册信息"""

        user_name = request.POST.get('user_name')
        pwd = request.POST.get('pwd')
        email = request.POST.get('email')
        allow = request.POST.get('allow')
        # 验校用户注册参数 只要有一个数据为空那么返回假,只有全部为真,才为真
        if not all([user_name, pwd, email]):
            return redirect(reverse('users:register'))
        # 邮箱格式
        if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return render(request, 'register.html', {'errmsg': '邮箱格式错误'})
        # 判断勾选框协议
        if allow != 'on':
             return render(request, 'register.html', {'errmage': '没有勾选用户协议'})
        # 保存用户注册参数
        try:
            user = User.objects.create_user(user_name, email, pwd)
        except db.IntegrityError:
            return render(request, 'register.html', {'errmsg': '用户已注册'})

        # 手动的将用户认证系统默认的激活状态is_active设置成False,默认是True
        user.is_active = False

        user.save()
        # 生成激活token
        token = user.generate_active_token()
        # 异步发送邮件,不能阻塞HttpResponse
        send_active_email.delay(email, user_name, token)

        return HttpResponse("这里是注册逻辑")


# def register(request):
#     """
#     函数视图, 注册:提供注册页面和实现注册逻辑
#     如果要在一个视图中,实现多种请求逻辑,请求地址使用相同的地址,只是请求方法不同而已
#     """
#
#     if request.method == 'GET':
#         """提供注册页面"""
#         return render(request, 'register.html')
#
#     if request.method == 'POST':
#         """处理注册逻辑,存储注册信息"""
#         return HttpResponse('这里是处理注册逻辑')


