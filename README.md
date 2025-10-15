# VuePress-Theme-Hope-IndexNow
兼容 VuePress Theme Hope 的 BING IndexNow 自动提交PY脚本


**如何使用？**

创建%CD%/sitemap_data/Settings.json

Settings.json内容

    {
                "sitemap_url": "https://你的域名/sitemap.xml",
                "host": "你的域名",
                "key": "IndexNowKEY"
    }
	

脚本首次运行时将提交完整的sitemap，后续运行则仅增量提交本地记录的变更与新增内容。

IndexNowKEY在 **https://www.bing.com/indexnow/getstarted** 获取。

此脚本是使用Deepseek生成的。