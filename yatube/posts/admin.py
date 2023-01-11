from django.contrib import admin

from .models import Group, Post


class PostAdmin(admin.ModelAdmin):
    list_display = (
        'pk',
        'text',
        'created',
        'author',
        'group',
    )
    list_editable = ('group',)  # Можно сразу выбирать
    search_fields = ('text',)
    list_filter = ('created',)
    empty_value_display = '-пусто-'

    def __str__(self) -> str:
        return self.text


admin.site.register(Post, PostAdmin)
admin.site.register(Group)
