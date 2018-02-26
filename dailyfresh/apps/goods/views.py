from django.shortcuts import render
from django.views.generic import View
# Create your views here.


class IndexView(View):
    """主页"""

    def get(self,request):
        return render(request, 'index.html')
        pass

