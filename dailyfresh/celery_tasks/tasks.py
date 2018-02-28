import os
from celery import Celery
from django.core.mail import send_mail
from django.conf import settings
from goods.models import GoodsCategory, IndexGoodsBanner, IndexPromotionBanner, IndexCategoryGoodsBanner
from django.template import loader
# 创建celery客户端celery对象
# 参数1 : 指定任务所有路径,从包名开始; 参数2:指定任务队列(broker)
app = Celery('celery_tasks.tasks', broker='redis://192.168.110.130:6379/4')


# 产生任务
@app.task
def send_active_email(to_email,user_name, token):
    """封装发送邮件的任务"""

    subject = "天天生鲜用户激活"  # 标题
    body = ""  # 文本邮件体
    sender = settings.EMAIL_FROM  # 发件人
    receiver = [to_email]  # 接收人
    html_body = '<h1>尊敬的用户 %s, 感谢您注册天天生鲜！</h1>' \
                '<br/><p>请点击此链接激活您的帐号<a href="http://127.0.0.1:8000/users/active/%s">' \
                'http://127.0.0.1:8000/users/active/%s</a></p>' % (user_name, token, token)
    send_mail(subject, body, sender, receiver, html_message=html_body)


@app.task
def generate_static_index_html():
    """异步静态页面"""

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

    # 查询购物车信息
    cart_num = 0

    # 构造上下文
    context = {
        'categorys': categorys,
        'banners': banners,
        'promotion_banners': promotion_banners,
        'cart_num': cart_num
    }
    # 加载模版
    template = loader.get_template('static_index.html')
    html_data = template.render(context)
    # 保存为html：放到静态文件
    # 保存成html文件:放到静态文件中
    file_path = os.path.join(settings.STATICFILES_DIRS[0], 'index.html')
    with open(file_path, 'w') as file:
        file.write(html_data)

    