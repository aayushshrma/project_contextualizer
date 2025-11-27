from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from core.vectorstore import search_similar


@require_GET  # accept GET requests
def semantic_search(request):
    q = request.GET.get("q", "")
    if not q:
        return JsonResponse({"error": "q parameter required"}, status=400)

    result = search_similar(q, n_results=5)
    payload = []
    for i in range(len(result["ids"][0])):
        payload.append({"id": result["ids"][0][i], "text": result["documents"][0][i],
                        "metadata": result["metadatas"][0][i]})
    return JsonResponse({"results": payload})
