def solve_community_identifier(request):
    # TODO: This is shitty
    if len(request.META["HTTP_HOST"].split(".")) < 3:
        return "riskofrain2"
    else:
        return request.META["HTTP_HOST"].split(".")[0]
