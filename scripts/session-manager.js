#!/usr/bin/env node
/**
 * Playwright Session Manager
 * 功能：多方式登录网站 + 保存Cookie + 后续自动恢复会话
 * 
 * 支持的登录方式：
 *   1. login-manual    - 打开浏览器让你随便登录（扫码/账号/短信都行），自动检测成功
 *   2. login           - 传入用户名密码，自动填表登录
 *   3. login-chrome    - 接管已登录的 Chrome 会话（需先 attached）
 *   4. login-cookie    - 直接注入 Cookie（从浏览器 DevTools 复制）
 * 
 * 用法：
 *   node session-manager.js login-manual <平台>
 *   node session-manager.js login <平台> <用户名> <密码或验证码>
 *   node session-manager.js login-chrome <平台>
 *   node session-manager.js login-cookie <平台> <cookie字符串>
 *   node session-manager.js scrape <平台> <URL> [等待ms]
 *   node session-manager.js status [平台]
 *   node session-manager.js clear <平台>
 * 
 * 环境变量：
 *   SESSION_DIR  - Cookie存储目录（默认 ~/.agent-browser/sessions/）
 *   HEADLESS    - 是否无头（false显示浏览器窗口）
 */

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const os = require('os');

// ========== 配置 ==========
const SESSION_DIR = process.env.SESSION_DIR || path.join(os.homedir(), '.agent-browser', 'sessions');

// 确保目录存在
if (!fs.existsSync(SESSION_DIR)) {
    fs.mkdirSync(SESSION_DIR, { recursive: true });
}

// ========== 平台配置 ==========
const PLATFORMS = {
    'yaozh': {
        name: '药智网',
        loginUrl: 'https://www.yaozh.com/login',
        loginSelector: {
            username: 'input[placeholder*="手机"]',
            password: 'input[placeholder*="密码"]',
            submit: 'button[type="submit"]',
            smsButton: 'button:has-text("获取验证码")',
        },
        waitAfterLogin: 3000,
        testUrl: 'https://db.yaozh.com/pijian',
        testText: '批准文号',
    },
    'kaisi': {
        name: '开思CHIS',
        loginUrl: 'https://agent.sinohealth.com/chis',
        loginSelector: {
            username: 'input[type="text"]',
            password: 'input[type="password"]',
            submit: 'button[type="submit"]',
        },
        waitAfterLogin: 5000,
        testUrl: 'https://agent.sinohealth.com/chis',
        testText: '市场数据库',
    },
    'douyin': {
        name: '抖音创作服务平台',
        loginUrl: 'https://creator.douyin.com/creator-micro/creator-count/arithmetic-index',
        loginSelector: {
            smsButton: 'button:has-text("获取验证码")',
            username: 'input[placeholder*="手机"]',
            code: 'input[placeholder*="验证码"]',
            submit: 'button:has-text("登录")',
        },
        waitAfterLogin: 3000,
        testUrl: 'https://creator.douyin.com/creator-micro/creator-count/arithmetic-index',
        testText: '关键词指数',
        type: 'sms', // 短信登录
    },
    'cma': {
        name: '中华医学会',
        loginUrl: 'https://www.cma.org.cn/col/col1702/index.html',
        loginSelector: {
            username: 'input[placeholder*="手机"]',
            password: 'input[placeholder*="密码"]',
            submit: 'button[type="submit"]',
        },
        waitAfterLogin: 3000,
        testUrl: 'https://www.cma.org.cn/',
        testText: '中华医学会',
    },
    'wanfang': {
        name: '万方数据',
        loginUrl: 'https://s.wanfangdata.com.cn',
        loginSelector: {
            username: 'input[placeholder*="手机"]',
            password: 'input[placeholder*="密码"]',
            submit: 'button[type="submit"]',
        },
        waitAfterLogin: 3000,
        testUrl: 'https://s.wanfangdata.com.cn',
        testText: '万方数据',
    },
    'cnki': {
        name: '知网CNKI',
        loginUrl: 'https://fsso.cnki.net',
        loginSelector: {
            username: 'input[name="username"]',
            password: 'input[name="password"]',
            submit: 'button[type="submit"]',
        },
        waitAfterLogin: 3000,
        testUrl: 'https://www.cnki.net',
        testText: '知网',
    },
    'dingxiang': {
        name: '丁香园药品数据库',
        loginUrl: 'https://www.dxy.cn/',
        loginSelector: {
            username: 'input[placeholder*="手机"]',
            password: 'input[placeholder*="密码"]',
            submit: 'button[type="submit"]',
        },
        waitAfterLogin: 3000,
        testUrl: 'https://db.dxy.cn/',
        testText: '丁香园',
        note: '丁香园与药智网功能部分重叠；优先用药智网；丁香园作为交叉验证备选',
    },
    'eleme': {
        name: '饿了么',
        loginUrl: 'https://www.ele.me/',
        loginSelector: {
            username: 'input[placeholder*="手机"]',
            password: 'input[placeholder*="密码"]',
            submit: 'button[type="submit"]',
        },
        waitAfterLogin: 3000,
        testUrl: 'https://www.ele.me/',
        testText: '饿了么',
        note: 'A03/A07 O2O备选平台；美团已覆盖主要O2O需求；饿了么补充蜂窝覆盖率',
    },
    'meituan': {
        name: '美团',
        loginUrl: 'https://www.meituan.com/',
        loginSelector: {
            username: 'input[placeholder*="手机"]',
            password: 'input[placeholder*="密码"]',
            submit: 'button[type="submit"]',
        },
        waitAfterLogin: 3000,
        testUrl: 'https://www.meituan.com/',
        testText: '美团',
        note: 'A03/A07 O2O主平台；查智搜/严选/智投付费推广状态、蜂窝覆盖率',
    },
    'nhsa': {
        name: '国家医保局',
        loginUrl: 'https://code.nhsa.gov.cn/home.html',
        loginSelector: {
            // 医保局数据查询多为公开数据，部分需维护入口登录
        },
        waitAfterLogin: 2000,
        testUrl: 'https://code.nhsa.gov.cn/toSearch.html?sysflag=1003',
        testText: '医保药品',
        note: 'A00 医保身份查询；公开查询入口，无需登录即可查西药中成药信息',
    },
    'nmpa': {
        name: '国家药监局数据查询',
        loginUrl: 'https://www.nmpa.gov.cn/datasearch/home-index.html',
        loginSelector: {
            // NMPA数据查询大多为公开数据
        },
        waitAfterLogin: 2000,
        testUrl: 'https://www.nmpa.gov.cn/datasearch/home-index.html',
        testText: '国家药品监督管理局',
        note: 'A00/A01/A04/A08/A09/A10/F01/F02数据来源；公开数据无需登录',
    },
};

// ========== 工具函数 ==========
function getPlatformKey(nameOrAlias) {
    const aliases = {
        '药智网': 'yaozh',
        '开思': 'kaisi', '开思CHIS': 'kaisi', 'kaisi': 'kaisi',
        '抖音': 'douyin', '抖音创作服务平台': 'douyin',
        '中华医学会': 'cma', 'cma': 'cma',
        '万方': 'wanfang', '万方数据': 'wanfang',
        '知网': 'cnki', 'cnki': 'cnki',
        '丁香园': 'dingxiang', '丁香园药品数据库': 'dingxiang', 'dingxiang': 'dingxiang',
        '饿了么': 'eleme', 'eleme': 'eleme',
        '美团': 'meituan', 'meituan': 'meituan',
        '国家医保局': 'nhsa', '医保局': 'nhsa', 'nhsa': 'nhsa',
        'nmpa': 'nmpa', '国家药监局': 'nmpa', '药监局': 'nmpa',
    };
    return aliases[nameOrAlias] || nameOrAlias;
}

function getCookiePath(platform) {
    return path.join(SESSION_DIR, `${platform}-cookies.json`);
}

function saveCookies(context, platform) {
    const cookiePath = getCookiePath(platform);
    // playwright 的 context.cookies() 返回数组
    return context.cookies().then(cookies => {
        fs.writeFileSync(cookiePath, JSON.stringify(cookies, null, 2));
        console.log(`✅ Cookie已保存: ${cookiePath} (${cookies.length}个)`);
        return cookies;
    });
}

async function loadCookies(context, platform) {
    const cookiePath = getCookiePath(platform);
    if (!fs.existsSync(cookiePath)) {
        console.log(`⚠️ 未找到Cookie文件: ${cookiePath}`);
        return [];
    }
    const cookies = JSON.parse(fs.readFileSync(cookiePath, 'utf8'));
    if (cookies.length === 0) {
        console.log(`⚠️ Cookie文件为空: ${cookiePath}`);
        return [];
    }
    // 设置 Cookie 的域名
    const domain = cookies[0]?.domain || '';
    await context.addCookies(cookies);
    console.log(`✅ 已加载${cookies.length}个Cookie from ${cookiePath}`);
    return cookies;
}

// ========== 命令处理 ==========

// node session-manager.js status <平台>
async function status(platform) {
    const key = getPlatformKey(platform);
    const cookiePath = getCookiePath(key);
    if (!fs.existsSync(cookiePath)) {
        console.log(`❌ ${platform}: 无会话（未登录）`);
        return;
    }
    const cookies = JSON.parse(fs.readFileSync(cookiePath, 'utf8'));
    const now = Date.now();
    // 找有过期时间的cookie
    const expirations = cookies
        .filter(c => c.expires)
        .map(c => new Date(c.expires).toLocaleString('zh-CN'))
        .filter(d => d !== 'Invalid Date');
    
    console.log(`✅ ${platform}: 有会话（${cookies.length}个Cookie）`);
    if (expirations.length > 0) {
        console.log(`   Cookie过期时间: ${expirations.join(', ')}`);
    }
}

// node session-manager.js clear <平台>
async function clear(platform) {
    const key = getPlatformKey(platform);
    const cookiePath = getCookiePath(key);
    if (fs.existsSync(cookiePath)) {
        fs.unlinkSync(cookiePath);
        console.log(`✅ ${platform}: 会话已清除`);
    } else {
        console.log(`ℹ️ ${platform}: 无会话可清除`);
    }
}

// node session-manager.js login <平台> <用户名> [密码]
async function login(platform, username, password) {
    const key = getPlatformKey(platform);
    const config = PLATFORMS[key];
    
    if (!config) {
        console.error(`❌ 未知平台: ${platform}`);
        console.error(`支持的平台: ${Object.keys(PLATFORMS).join(', ')}`);
        process.exit(1);
    }
    
    console.log(`🔐 正在登录 ${config.name}...`);
    
    const browser = await chromium.launch({
        headless: process.env.HEADLESS !== 'false',
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-blink-features=AutomationControlled',
        ],
    });
    
    const context = await browser.newContext({
        userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
        viewport: { width: 375, height: 812 },
    });
    
    // 隐藏自动化特征
    await context.addInitScript(() => {
        Object.defineProperty(navigator, 'webdriver', { get: () => false });
        window.chrome = { runtime: {} };
    });
    
    const page = await context.newPage();
    
    console.log(`📱 打开登录页: ${config.loginUrl}`);
    await page.goto(config.loginUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });
    
    // 等待页面加载
    await page.waitForTimeout(2000);
    
    const sel = config.loginSelector;
    
    if (config.type === 'sms') {
        // 短信登录流程
        console.log(`📱 使用短信登录...`);
        
        // 输入手机号
        if (sel.username && username) {
            await page.fill(sel.username, username);
            console.log(`   手机号: ${username}`);
        }
        
        // 点击获取验证码
        if (sel.smsButton) {
            await page.click(sel.smsButton);
            console.log(`   已点击获取验证码`);
        }
        
        // 等待用户输入验证码（在这里暂停，让用户手动输入）
        // 或者通过参数传入验证码
        if (password) {
            // 假设密码参数实际上是验证码
            console.log(`   等待10秒让验证码生效...`);
            await page.waitForTimeout(10000);
            
            if (sel.code) {
                await page.fill(sel.code, password);
                console.log(`   验证码已填写`);
            }
        } else {
            console.log(`⚠️ 需要验证码，请手动在浏览器中完成登录`);
            console.log(`   然后按回车继续...`);
            await new Promise(resolve => {
                process.stdin.once('data', resolve);
            });
        }
        
        // 提交
        if (sel.submit) {
            await page.click(sel.submit);
            console.log(`   已提交`);
        }
        
    } else {
        // 用户名密码登录
        if (sel.username && username) {
            await page.fill(sel.username, username);
            console.log(`   用户名: ${username}`);
        }
        
        if (sel.password && password) {
            await page.fill(sel.password, password);
            console.log(`   密码: ****`);
        }
        
        // 提交
        if (sel.submit) {
            await page.click(sel.submit);
            console.log(`   已提交登录`);
        }
    }
    
    // 等待登录结果
    console.log(`⏳ 等待${config.waitAfterLogin}ms...`);
    await page.waitForTimeout(config.waitAfterLogin);
    
    // 检查是否登录成功
    try {
        await page.goto(config.testUrl, { waitUntil: 'domcontentloaded', timeout: 15000 });
        await page.waitForTimeout(2000);
        
        const content = await page.evaluate(() => document.body.innerText);
        if (content.includes(config.testText)) {
            console.log(`✅ 登录成功！`);
        } else {
            console.log(`⚠️ 登录结果不确定，页面内容不包含"${config.testText}"`);
        }
    } catch (e) {
        console.log(`⚠️ 登录后跳转失败: ${e.message}`);
    }
    
    // 保存Cookie
    await saveCookies(context, key);
    
    // 截图保存
    const screenshotPath = getCookiePath(key).replace('.json', '-login.png');
    await page.screenshot({ path: screenshotPath, fullPage: false });
    console.log(`📸 截图已保存: ${screenshotPath}`);
    
    await browser.close();
}

// node session-manager.js scrape <平台> <URL> [等待时间]
async function scrape(platform, url, waitTime) {
    const key = getPlatformKey(platform);
    const config = PLATFORMS[key];
    
    console.log(`🕷️ 爬取 ${url} (平台: ${config ? config.name : platform})`);
    
    const browser = await chromium.launch({
        headless: process.env.HEADLESS !== 'false',
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-blink-features=AutomationControlled',
        ],
    });
    
    const context = await browser.newContext({
        userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
        viewport: { width: 375, height: 812 },
    });
    
    // 隐藏自动化特征
    await context.addInitScript(() => {
        Object.defineProperty(navigator, 'webdriver', { get: () => false });
        window.chrome = { runtime: {} };
    });
    
    // 尝试恢复Cookie
    await loadCookies(context, key);
    
    const page = await context.newPage();
    
    console.log(`📱 导航到: ${url}`);
    try {
        const response = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
        console.log(`📡 HTTP Status: ${response.status()}`);
        
        const wait = parseInt(waitTime) || 5000;
        console.log(`⏳ 等待${wait}ms让内容加载...`);
        await page.waitForTimeout(wait);
        
        // 检查是否跳转到登录页（更精准的判断）
        const currentUrl = page.url();
        const pageText = await page.evaluate(() => document.body.innerText);
        const isLoginPage = await page.evaluate(() => {
            // 精准判断：检查是否有登录表单（用户名/密码输入框）
            const hasLoginForm = !!(
                document.querySelector('input[type="password"]') ||
                document.querySelector('input[placeholder*="密码"]') ||
                document.querySelector('input[placeholder*="手机"]') ||
                document.querySelector('input[name="username"]') ||
                document.querySelector('form[action*="login"]')
            );
            // 同时检查URL是否明确包含login
            const urlHasLogin = window.location.href.includes('login') ||
                                window.location.href.includes('Login') ||
                                window.location.href.includes('signin');
            return { hasLoginForm, urlHasLogin };
        });
        
        if (isLoginPage.hasLoginForm || (isLoginPage.urlHasLogin && currentUrl.includes('login'))) {
            console.log(`⚠️ 检测到登录页，Cookie可能已过期`);
            console.log(`   当前URL: ${currentUrl}`);
            // 截图保存登录页
            const screenshotPath = getCookiePath(key).replace('.json', '-login-page.png');
            await page.screenshot({ path: screenshotPath, fullPage: false });
            console.log(`📸 登录页截图: ${screenshotPath}`);
        } else {
            console.log(`✅ 页面加载成功`);
            
            // 保存页面内容
            const result = {
                url: currentUrl,
                title: await page.title(),
                content: pageText.substring(0, 5000),
                contentLength: pageText.length,
            };
            
            // 保存HTML
            const htmlPath = getCookiePath(key).replace('.json', `-${Date.now()}.html`);
            fs.writeFileSync(htmlPath, await page.content());
            console.log(`📄 HTML已保存: ${htmlPath}`);
            result.htmlFile = htmlPath;
            
            console.log(JSON.stringify(result, null, 2));
            return result;
        }
    } catch (error) {
        console.error(`❌ 爬取失败: ${error.message}`);
    }
    
    await browser.close();
}

// ========== 方式二：手动登录（支持扫码/任意方式，自动检测成功） ==========
// 打开浏览器，到登录页，用户随便用什么方式登录（扫码/账号/短信），我自动检测成功后保存Cookie
async function doManualLogin(key) {
    const config = PLATFORMS[key];
    if (!config) {
        console.error(`❌ 未知平台: ${key}`);
        process.exit(1);
    }

    console.log(`\n🖥️ 手动登录 - ${config.name}`);
    console.log(`   支持：账号密码、短信验证码、微信扫码、App扫码 等任意方式`);
    console.log(`   浏览器将打开登录页，你完成登录后自动检测并保存Cookie\n`);

    const browser = await chromium.launch({
        headless: false, // 必须显示窗口，否则无法手动操作
        args: ['--no-sandbox', '--disable-setuid-sandbox'],
    });

    const context = await browser.newContext({
        userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        viewport: { width: 1280, height: 800 },
    });

    // 隐藏自动化特征
    await context.addInitScript(() => {
        Object.defineProperty(navigator, 'webdriver', { get: () => false });
    });

    const page = await context.newPage();
    await page.goto(config.loginUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });
    console.log(`✅ 已打开登录页: ${config.loginUrl}`);

    // 检测是否已处于登录状态（有时候Cookie还在）
    if (await isLoggedIn(page, config)) {
        console.log(`ℹ️ 检测到已登录（Cookie未过期），直接保存...`);
    } else {
        console.log(`\n⏳ 等待你完成登录...`);
        console.log(`   支持方式：账号密码 | 短信验证码 | 微信扫码 | App扫码`);
        console.log(`   检测到登录成功后自动保存Cookie并关闭浏览器\n`);

        // 轮询检测登录状态（每2秒检查一次）
        let attempts = 0;
        const maxAttempts = 150; // 最多等5分钟
        while (attempts < maxAttempts) {
            await page.waitForTimeout(2000);
            attempts++;

            if (await isLoggedIn(page, config)) {
                console.log(`\n✅ 检测到登录成功！`);
                break;
            }

            // 进度提示（每30秒打印一次）
            if (attempts % 15 === 0) {
                console.log(`   ⏳ 仍在等待...（已等${Math.floor(attempts * 2 / 60)}分${attempts * 2 % 60}秒，可继续操作浏览器）`);
            }
        }

        if (attempts >= maxAttempts) {
            console.log(`\n⚠️ 等待超时，请确认是否已完成登录`);
            console.log(`   如果已完成登录，请在此终端按回车继续...`);
            await new Promise(resolve => process.stdin.once('data', resolve));
        }
    }

    // 保存Cookie
    await saveCookies(context, key);
    console.log(`💾 Cookie已保存: ${getCookiePath(key)}`);

    // 截图保存
    await page.screenshot({ path: getCookiePath(key).replace('.json', '-login-success.png'), fullPage: true });
    console.log(`📸 截图已保存`);

    await browser.close();
    console.log(`✅ 手动登录完成！\n`);
}

// 检测页面是否已登录（通用逻辑，适用于大多数平台）
async function isLoggedIn(page, config) {
    try {
        const url = page.url();
        // 如果URL变成非登录页，通常意味着已登录
        if (!url.includes('login') && !url.includes('signin') && !url.includes('Login')) {
            // 进一步检查页面上是否有登录相关的输入框
            const hasLoginForm = await page.evaluate(() => {
                return !!(
                    document.querySelector('input[type="password"]:not([style*="hidden"])') ||
                    document.querySelector('input[placeholder*="密码"]') ||
                    document.querySelector('input[placeholder*="手机"][name!=""]') ||
                    document.querySelector('input[placeholder*="账号"]')
                );
            });
            if (!hasLoginForm) {
                return true;
            }
        }
        // 检查是否有"退出"或用户信息元素（更准确）
        const pageText = await page.evaluate(() => document.body.innerText);
        const isLoggedInKeywords = ['退出', '退出登录', '我的', '会员', 'VIP', '我的账户', '我的资料', '个人中心', '账号设置'];
        if (isLoggedInKeywords.some(kw => pageText.includes(kw))) {
            // 确认不是登录页
            if (!url.includes('login')) {
                return true;
            }
        }
    } catch (e) {
        // ignore
    }
    return false;
}

// ========== 方式三：接管已登录的 Chrome 会话 ==========
// 通过浏览器工具 profile="chrome" 使用，无需额外处理
// 此函数作为占位说明，实际由 browser tool 自动处理
async function doChromeAttach(key) {
    const config = PLATFORMS[key];
    console.log(`\n🔗 Chrome会话接管 - ${config ? config.name : key}`);
    console.log(`   方式：使用 browser tool (profile="chrome") 自动接管你的Chrome标签页`);
    console.log(`   前提：你已通过 Browser Relay 插件 attached 标签页`);
    console.log(`   说明：此平台无需单独保存Cookie，直接用 browser tool 即可\n`);
}

// ========== 方式四：直接注入 Cookie ==========
async function doCookieInject(key, cookieStr) {
    const config = PLATFORMS[key];
    console.log(`\n🍪 Cookie注入 - ${config ? config.name : key}`);

    let cookies;
    try {
        cookies = JSON.parse(cookieStr);
        if (!Array.isArray(cookies)) cookies = [cookies];
    } catch (e) {
        // 尝试解析为 name=value; pairs
        cookies = cookieStr.split(';').map(c => {
            const [name, ...rest] = c.trim().split('=');
            return { name: name.trim(), value: rest.join('=').trim(), domain: config && config.cookieDomain || '.yaozh.com' };
        });
    }

    const browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });
    const context = await browser.newContext();
    await context.addCookies(cookies);
    await saveCookies(context, key);
    await browser.close();
    console.log(`✅ Cookie已注入并保存: ${getCookiePath(key)}\n`);
}

// ========== 主入口 ==========
const [,, command, ...args] = process.argv;

switch (command) {
    case 'login':
        // login <平台> <用户名> [密码/验证码] — 自动化填表
        login(args[0], args[1], args[2]);
        break;
    case 'login-manual':
        // login-manual <平台> — 推荐方式：打开浏览器随便登录，自动检测成功
        doManualLogin(getPlatformKey(args[0]));
        break;
    case 'login-chrome':
        // login-chrome <平台> — 用 browser tool profile="chrome" 接管已登录会话
        doChromeAttach(getPlatformKey(args[0]));
        break;
    case 'login-cookie':
        // login-cookie <平台> <cookie字符串或JSON> — 直接注入Cookie
        doCookieInject(getPlatformKey(args[0]), args.slice(1).join(' '));
        break;
    case 'scrape':
        scrape(args[0], args[1], args[2]);
        break;
    case 'status':
        status(args[0]);
        break;
    case 'clear':
        clear(args[0]);
        break;
    default:
        console.log(`
🕷️ Playwright Session Manager - 会话管理工具（多登录方式）

用法:
  node session-manager.js login-manual <平台>   ⭐推荐：打开浏览器随便登录，自动检测保存
  node session-manager.js login <平台> <用户名> <密码或验证码>  # 自动化填表
  node session-manager.js login-chrome <平台>    # 用 browser tool profile="chrome" 接管
  node session-manager.js login-cookie <平台> <cookie>  # 从DevTools复制Cookie注入
  node session-manager.js scrape <平台> <URL> [等待ms]
  node session-manager.js status [平台]
  node session-manager.js clear <平台>

登录方式说明:
  login-manual    ⭐最推荐⭐ 打开浏览器，你用任何方式登录（扫码/账号/短信），
                   自动检测成功后保存Cookie，支持所有平台所有登录方式
  login           传用户名密码，自动填表（适合固定账号场景）
  login-chrome    用 browser tool (profile="chrome") 直接接管已登录的Chrome标签页
                   前提：Chrome已安装OpenClaw Browser Relay插件，标签页已 attached
  login-cookie    从浏览器开发者工具 Application > Cookies 复制，JSON或字符串格式

支持的平台:
  yaozh      - 药智网（批文/说明书/VIP市场数据）
  kaisi      - 开思CHIS（市场盘子/品牌份额）🔴必备账号
  douyin     - 抖音创作服务平台（关键词指数）
  cma        - 中华医学会（指南共识）
  wanfang    - 万方数据（临床文献）
  cnki       - 知网CNKI（临床文献）
  dingxiang  - 丁香园药品数据库（批文备选）
  eleme      - 饿了么（O2O备选）
  meituan    - 美团（O2O主平台）
  nhsa       - 国家医保局（医保身份）
  nmpa       - 国家药监局（批文数据，公开无需登录）

示例:
  # 推荐：手动登录药智网（扫码/账号/短信随便用）
  node session-manager.js login-manual yaozh

  # 自动化登录（传用户名密码）
  node session-manager.js login yaozh 13800138000 mypassword

  # Chrome已登录时用 browser tool 接管（见 login-chrome 说明）
  node session-manager.js login-chrome yaozh

  # 查看会话状态
  node session-manager.js status yaozh

  # 用已登录会话抓取数据
  node session-manager.js scrape yaozh https://db.yaozh.com/pijian?comprehensivesearchcontent=门冬氨酸钙

  # 清除会话（重新登录）
  node session-manager.js clear yaozh

环境变量:
  SESSION_DIR  - Cookie存储目录（默认 ~/.agent-browser/sessions/）
  HEADLESS    - 是否无头（false=显示浏览器窗口，login-manual必须为false）
`);
}

module.exports = { login, doManualLogin, scrape, status, clear, loadCookies, saveCookies, PLATFORMS };
