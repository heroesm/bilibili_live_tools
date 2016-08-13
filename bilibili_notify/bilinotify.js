// ==UserScript==
// @name        bilibili notify
// @namespace   heroesm
// @include     http://live.bilibili.com/feed/getList/1
// @version     1
// @grant       none
// 
// ==/UserScript==
function main(){
    var running = true;
    var rProFilter, rConFilter;
    var rFilter = /./;
    var sMode = 'pro';
    var aTimer = [];
    function prepare(){
        Document.prototype.$ = Document.prototype.querySelector;
        Element.prototype.$ = Element.prototype.querySelector;
        Document.prototype.$$ = Document.prototype.querySelectorAll;
        Element.prototype.$$ = Element.prototype.querySelectorAll;
    }
    function start(){
        var timer = setTimeout(function(){
            window.location.reload();
        }, 30000);
        aTimer.push(timer);
        document.$('#pause').style.display = 'unset';
        document.$('#start').style.display = 'none';
        return timer;
    }
    function stop(){
        var nTimer = aTimer.pop();
        while (nTimer){
            clearTimeout(nTimer);
            nTimer = aTimer.pop();
        }
        document.$('#pause').style.display = 'none';
        document.$('#start').style.display = 'unset';
    }
    function update(){
        try{
            localStorage.bilinotify_con = document.$('#con').value;
            rConFilter = new RegExp(document.$('#con').value);
            localStorage.bilinotify_pro = document.$('#pro').value;
            rProFilter = new RegExp(document.$('#pro').value);
        }catch(e){console.log(e);}
        localStorage.bilinotify_mod = sMode = document.$('input[name=mode]:checked').value;
        if (sMode == 'pro'){
            rFilter = rProFilter;
        }
        else{
            rFilter = rConFilter; 
        }
    }
    function checkopen(item){
        var con = Boolean(sMode == 'con');
        if(con ^ rFilter.test(item.nickname)){
            window.open(item.link + '###', item.nickname);
        }
    }
    function build(){
        style = document.createElement('style');
        style.id = 'bilinotify_css';
        style.innerHTML = [
            'input[type=text] {width: 50%;}'
        ].join('\n');
        document.head.appendChild(style);
        document.body.insertAdjacentHTML(
            'beforeend',
            [
                '<div class="con">',
                '    <input type="radio" name="mode" value="con">',
                '    <span>使用该正则表达式按昵称进行排除：</span>',
                '<input id="con" type="text" placeholder="不想看的A的昵称|B的昵称|C的昵称">',
                '</div>',
                '<div class="pro">',
                '    <input type="radio" name="mode" value="pro" checked>',
                '    <span>使用该正则表达式按昵称进行匹配：</span>',
                '    <input id="pro" type="text" placeholder="想看的A的昵称|B的昵称|C的昵称">',
                '</div>',
                '<div>',
                '    <button id="confirm">确认</button>',
                '    <button id="pause">暂停</button>',
                '    <button id="start">继续</button>',
                '</div>'
            ].join('\n')
        );
        if (localStorage.bilinotify_con){
            document.$('#con').value = localStorage.bilinotify_con;
        }
        if (localStorage.bilinotify_pro){
            document.$('#pro').value = localStorage.bilinotify_pro;
        }
        if (localStorage.bilinotify_mod){
            document.$('input[type=radio][value=' + localStorage.bilinotify_mod + ']').checked = true;
        }
        update();
        document.$('#confirm').onclick = update;
        document.$('#start').onclick = start;
        document.$('#pause').onclick = stop;
    }
    function run(){
        try{
            prepare();
        }catch(e){}
        Obj = JSON.parse(document.body.childNodes[0].textContent.slice(1,-2));
        build();
        Data = Obj.data;
        if(Data.count>0) {
            document.title = "(！)有" + Data.count + "个直播";
            for(var x=0; x<Data.count; x++){
                item = Data.list[x];
                document.body.insertAdjacentHTML(
                    'beforeend', 
                    [
                        '<br />',
                        '<br />',
                        '<div style="clear:both;">',
                        '    <a style="float:left;" href="${item.link}"><img style="width:100px; height: 100px;" src="${item.face}"></img></a>',
                        '    <div style="float:left;">',
                        '        <span>${item.nickname}</span>',
                        '        <br>',
                        '        <a href="${item.link}">${item.roomname}</a>',
                        '    </div>',
                        '</div>'
                    ].join('\n').replace(/\$\{([^\}]+)\}/g, function(sMatch, sP1){
                        return eval(sP1);
                    })
                );
                checkopen(item);
            }
        }
        else{
            document.body.insertAdjacentHTML('beforeend', '<br /><br />无直播');
            document.title = "无直播";
        }

        start();
    }
    
    run();
}

try{
    main();
}catch(e){console.log(e.toString());}
