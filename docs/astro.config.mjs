import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

export default defineConfig({
    site: 'https://docs.trickfirerobotics.com',
    base: '/urc',
    srcDir: './',
    integrations: [
        starlight({
            title: 'TrickFire URC Documentation',
            head: [
                {
                    tag: 'script',
                    content: `
                        if (!localStorage.getItem('starlight-theme')) {
                            localStorage.setItem('starlight-theme', 'dark');
                        }
                    `
                }
            ],
            logo: {
                src: './assets/nav-logo.png',
                alt: 'TrickFire Robotics Logo',
                replacesTitle: true
            },
            favicon: '/favicon.ico',
            social: [
                {
                    icon: 'github',
                    label: 'GitHub',
                    href: 'https://github.com/TrickfireRobotics/urc'
                },
                {
                    icon: 'external',
                    label: 'Notion',
                    href: 'https://www.notion.so/trickfire/invite/7f153eec8ed8ebe4608dc95892fce859540f8640'
                },
                {
                    icon: 'external',
                    label: 'TrickFire Robotics',
                    href: 'https://trickfirerobotics.github.io'
                }
            ],
            sidebar: [
                { label: 'Home', items: [{ label: 'Temporary Home', slug: 'temp/temp' }] },
            ],
            components: {
                SocialIcons: './components/SocialIcons.astro'
            },
            customCss: ['./styles/custom.css']
        })
    ]
});
