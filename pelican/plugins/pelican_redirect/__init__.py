import logging
import os

from typing import Dict

from pelican import signals, contents
from pelican.generators import ArticlesGenerator, CachingGenerator, PagesGenerator

logger = logging.getLogger(__name__)


TEMPLATE = """\
<!DOCTYPE html>
<html>

<head>
    <link rel="canonical" href="/{{ page.save_as }}" />
    <meta http-equiv="content-type" content="text/html; charset=utf-8" />
    <meta http-equiv="refresh" content="0;url=/{{ page.save_as }}" />
</head>

<body>
<p>This content has moved. If you are not redirected, please click here:</p>
<p><a href="/{{ page.save_as }}">{{ page.save_as }}</a></p>
</body>

</html>
"""


class Redirect:
    def __init__(self, to: contents.Content, from_url: str):
        self.to = to
        if from_url[-1] == '/' or os.path.splitext(from_url)[-1] == '':
            self.from_url = from_url + ('' if from_url[-1] == '/' else '/') + 'index.html'
        else:
            self.from_url = from_url


class RedirectGenerator(CachingGenerator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.redirects = []
        signals.article_generator_finalized.connect(self.redirect_articles)
        signals.page_generator_finalized.connect(self.redirect_pages)
        self._templates["redirect"] = self.env.from_string(TEMPLATE)

    def redirect_articles(self, article_generator: ArticlesGenerator):
        for article in article_generator.articles:
            for url in self.redirected_urls(article_generator, article, kind="ARTICLE"):
                self.redirects.append(Redirect(to=article, from_url=url))

    def redirect_pages(self, page_generator: PagesGenerator):
        for page in page_generator.pages:
            for url in self.redirected_urls(page_generator, page, kind="PAGE"):
                self.redirects.append(Redirect(to=page, from_url=url))

    def redirected_urls(self, generator: CachingGenerator, page, kind):
        for formats in generator.settings.get("CONTENT_REDIRECT_CONFIGURATION", []):
            if f"{kind}_URL" in formats:
                yield formats[f"{kind}_URL"].format(**page.url_format)

        if page.metadata.get("original_url"):
            yield page.metadata.get("original_url")

    def generate_output(self, writer) -> None:
        for redirector in self.redirects:
            logger.debug(
                "\nSource Path: %s\nRedirect File: %s",
                redirector.to,
                redirector.from_url,
            )
            writer.write_file(
                redirector.from_url,
                self.get_template("redirect"),
                self.context,
                self.settings["RELATIVE_URLS"],
                paginated=False,
                page=redirector.to,
            )


def get_generators(pelican_object):
    return RedirectGenerator


def register():
    signals.get_generators.connect(get_generators)
