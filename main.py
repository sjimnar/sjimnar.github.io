def define_env(env):
    """
    This is the hook for the Griffe-generated macros.
    - env: the environment for this macro
    """
    @env.macro
    def tags():
        if not hasattr(env.variables.get('page'), 'tags'):
            return "" # No tags available

        # Access the blog plugin's tags data
        blog_plugin = env.plugins.get_plugin('blog')
        if not blog_plugin:
            return "" # Blog plugin not found

        tags_data = blog_plugin.tags

        if not tags_data:
            return "" # No tags found in blog posts

        # Generate a simple tag cloud HTML
        html = '<div class="tag-cloud">'
        for tag_name, tag_info in sorted(tags_data.items()):
            # tag_info.url is the URL to the tag page
            html += f'<a href="{tag_info.url}" class="tag tag-{tag_name.replace(" ", "-").lower()}">{tag_name} ({len(tag_info.posts)})</a> '
        html += '</div>'
        return html
