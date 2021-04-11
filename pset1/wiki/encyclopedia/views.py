from django.shortcuts import render
from . import util
from django.http import HttpResponse
import markdown2
from django import forms
from django.http import HttpResponseRedirect
from django.urls import reverse

class SearchForm(forms.Form):
	title = forms.CharField(label="", widget=forms.TextInput(attrs={"class": "search", "placeholder": "Search Encyclopedia"}))

class CreateForm(forms.Form):
    title = forms.CharField(label="Title")
    content = forms.CharField(label="Markdown", widget=forms.Textarea)

def index(request):
    if request.method == "POST":
        form = SearchForm(request.POST)
        if form.is_valid():
            title = form.cleaned_data["title"]
            newTitle = findMatching(title)
            if newTitle != None:
                return HttpResponseRedirect(reverse("entry", kwargs={"title": newTitle}))
            return render(request, "encyclopedia/search.html", {
                "title": title,
                "entries": generateResults(title),
                "searchForm": SearchForm()
            })
            
    return render(request, "encyclopedia/index.html", {
        "entries": util.list_entries(),
        "searchForm": SearchForm()
    })

def entry(request, title):
    contents = util.get_entry(title)
    if contents == None:
        return HttpResponse("Page not found")
    return render(request, "encyclopedia/entry.html", {
        "title": title,
        "contents": markdown2.markdown(contents),
        "searchForm": SearchForm()
    })

def create(request):
    if request.method == "POST":
        form = CreateForm(request.POST)
        if form.is_valid():
            title = form.cleaned_data["title"]
            content = form.cleaned_data["content"]
            if title in util.list_entries():
                return HttpResponse("Page already exists")
            util.save_entry(title, content)
            return HttpResponseRedirect(reverse("index"))
        
    return render(request, "encyclopedia/create.html", {
        "searchForm": SearchForm(),
        "createForm": CreateForm()
    })

def findMatching(title):
    for entry in util.list_entries():
        if title.upper() == entry.upper():
            return entry
    return None

def generateResults(query):
    results = []
    for entry in util.list_entries():
        if query.upper() in entry.upper():
            results.append(entry)
    return results
