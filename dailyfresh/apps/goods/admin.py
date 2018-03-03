from django.contrib import admin
from goods.models import GoodsCategory, Goods, GoodsSKU, IndexGoodsBanner, IndexCategoryGoodsBanner,IndexPromotionBanner
from celery_tasks.tasks import generate_static_index_html
from django.core.cache import cache
# Register your models here.


class BaseAdmin(admin.ModelAdmin):
        """商品活动信息的管理类，运营人员在后台发布内容时， 异步生成静态页面"""

        def save_model(self, request, obj, form, change):
            """后台保存对象数据时使用"""
            # obj表示要保存的对象，调用save(),将对象保存到数据库中
            obj.save()
            # 调用celery异步生成静态文件
            generate_static_index_html.delay()
            cache.delete('index_page_data')

        def delete_model(self, request, obj):
            """后台保存对象数据时使用"""
            obj.delete()
            generate_static_index_html.delay()
            cache.delete('index_page_data')


class IndexPromotionBannerAdmin(BaseAdmin):
    """商品活动站点管理，如果有自己的新的逻辑也是写在这里"""
    # list_display = []
    pass


class GoodsCategoryAdmin(BaseAdmin):
    pass


class GoodsAdmin(BaseAdmin):
    pass


class GoodsSKUAdmin(BaseAdmin):
    pass


class IndexCategoryGoodsBannerAdmin(BaseAdmin):
    pass


admin.site.register(GoodsCategory, GoodsCategoryAdmin)
admin.site.register(Goods, GoodsAdmin)
admin.site.register(GoodsSKU, GoodsSKUAdmin)
admin.site.register(IndexPromotionBanner, IndexPromotionBannerAdmin)
admin.site.register(IndexCategoryGoodsBanner, IndexCategoryGoodsBannerAdmin)
