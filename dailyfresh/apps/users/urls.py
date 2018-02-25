from django.conf.urls import url
from users import views
from django.contrib.auth.decorators import login_required

urlpatterns = [
    # 函数注册
    # url(r'^register$', views.register, name='register'),
    # 类视图实现注册
    url(r'^register$', views.RegisterView.as_view(), name='register'),
    # 邮件激活
    url(r'^active/(?P<token>.+)$', views.ActiveView.as_view(), name='active'),
    url(r'^login$', views.LoginView.as_view(), name='login'),
    url(r'^logout$', views.LogoutView.as_view(), name='logout'),

    # 装饰器@login_required作用于URL正则匹配中
    # 装饰器就是将函数当做参数传入，并通过inner函数返回。而且可以手动调用执行。
    # 因为，views.AddressView.as_view()的返回值就是类视图AddressView对应的函数视图
    # 所以，可以将views.AddressView.as_view()的返回值直接传给装饰器@login_required进行手动调用执行
    # 存在问题：限制页面访问是视图层的逻辑，不建议放在URL中完成，依然交由视图完成
    # url(r'^address$', login_required(views.AddressView.as_view()), name='address'),
    url(r'^address$', views.AddressView.as_view(), name='address'),
    url(r'^info$', views.UserInfoView.as_view(), name='info')
  ]