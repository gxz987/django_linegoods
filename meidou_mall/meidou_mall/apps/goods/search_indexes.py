from haystack import indexes

from .models import SKU


class SKUIndex(indexes.SearchIndex, indexes.Indexable):
    """
    SKU索引数据模型类
    """
    # 作用:1.明确在搜索引擎中索引数据包含哪些字段
    # 2.字段也会作为前端进行检索查询时关键词的参数名

    # text是用于搜索的
    text = indexes.CharField(document=True, use_template=True)

    # 其他字段是给系列化器提供返回内容的的
    id = indexes.IntegerField(model_attr='id')
    name = indexes.CharField(model_attr='name')
    price = indexes.DecimalField(model_attr='price')
    default_image_url = indexes.CharField(model_attr='default_image_url')
    comments = indexes.IntegerField(model_attr='comments')

    def get_model(self):
        """返回建立索引的模型类"""
        return SKU

    def index_queryset(self, using=None):
        """返回要建立索引的数据查询集"""
        # 指明数据库数据建立索引的范围
        # is_launched 是否上架销售
        # return SKU.objects.filter(is_launched=True)
        return self.get_model().objects.filter(is_launched=True)