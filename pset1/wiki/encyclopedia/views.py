from django.shortcuts import render
from . import util
from django.http import HttpResponse
import markdown2
from django import forms
from django.http import HttpResponseRedirect
from django.urls import reverse

class NewTaskForm(forms.Form):
	title = forms.CharField(label="", widget=forms.TextInput(attrs={"class": "search", "placeholder": "Search Encyclopedia"}))

def index(request):
    if request.method == "POST":
        form = NewTaskForm(request.POST)
        if form.is_valid():
            title = form.cleaned_data["title"]
            newTitle = findMatching(title)
            if newTitle != None:
                return HttpResponseRedirect(reverse("entry", kwargs={"title": newTitle}))
            return render(request, "encyclopedia/search.html", {
                "title": title,
                "entries": generateResults(title),
                "form": NewTaskForm()
            })
            
    return render(request, "encyclopedia/index.html", {
        "entries": util.list_entries(),
        "form": NewTaskForm()
    })

def entry(request, title):
    contents = util.get_entry(title)
    if contents == None:
        return HttpResponse("Page not found")
    return render(request, "encyclopedia/entry.html", {
        "title": title,
        "contents": markdown2.markdown(contents),
        "form": NewTaskForm()
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
