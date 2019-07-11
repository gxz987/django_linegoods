from django.contrib import admin

from . import models
# Register your models here.


# 商品 sku
class SKUAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        obj.save()
        from celery_tasks.html.tasks import generate_static_sku_detail_html
        generate_static_sku_detail_html(obj.id)

    # 商品对象sku删除方法不用重写,因为删除后无需做其他动作


# 商品规格
class SKUSpecificationAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        obj.save()
        from celery_tasks.html.tasks import generate_static_sku_detail_html
        generate_static_sku_detail_html(obj.sku.id)

    def delete_model(self, request, obj):
        sku_id = obj.sku.id
        obj.delete()
        from celery_tasks.html.tasks import generate_static_sku_detail_html
        generate_static_sku_detail_html(sku_id)


class SkUImageAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        # obj -> SKUImage 对象  obj.sku
        obj.save()
        from celery_tasks.html.tasks import generate_static_sku_detail_html
        generate_static_sku_detail_html(obj.sku.id)

        # 设置SKU默认图片
        sku = obj.sku
        if not sku.default_image_url:
            # http://image.meiduo.site:8888/groupxxxxxx
            sku.default_image_url = obj.image.url
            sku.save()

    def delete_model(self, request, obj):
        sku_id = obj.sku.id
        obj.delete()
        from celery_tasks.html.tasks import generate_static_sku_detail_html
        generate_static_sku_detail_html(sku_id)


admin.site.register(models.GoodsCategory)
admin.site.register(models.GoodsChannel)
admin.site.register(models.Goods)
admin.site.register(models.Brand)
admin.site.register(models.GoodsSpecification)
admin.site.register(models.SpecificationOption)
admin.site.register(models.SKU, SKUAdmin)
admin.site.register(models.SKUSpecification, SKUSpecificationAdmin)
admin.site.register(models.SKUImage, SkUImageAdmin)