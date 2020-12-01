import textwrap

def wrapTextInRegion(context, text):
    width = context.region.width - 10
    wrapper = textwrap.TextWrapper(width = int(width / 7))
    return wrapper.wrap(text = text)