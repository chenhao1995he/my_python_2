from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.views.generic import View
# 反向解析
from django.core.urlresolvers import reverse
from users.models import User
from django import db
from celery_tasks.tasks import send_active_email
import re

# Create your views here.


class ActiveView(View):
    """邮件激活"""
    def get(self, request, token):
        """处理激活请求"""
        pass


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


