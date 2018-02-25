from django.conf.urls import url
from users import views


urlpatterns = [
    # 函数注册
    # url(r'^register$', views.register, name='register'),
    # 类视图实现注册
    url(r'^register$', views.RegisterView.as_view(), name='register'),
    # 邮件激活
    url(r'^active/(?P<token>.+)$', views.ActiveView.as_view(), name='active'),
    url(r'^login$', views.LoginView.as_view(), name='login'),
    url(r'^logout$', views.LogoutView.as_view(), name='logout'),
  ]