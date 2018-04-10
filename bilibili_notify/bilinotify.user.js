// ==UserScript==
// @name        bilibili notify
// @namespace   heroesm
// @include     http://live.bilibili.com/feed/getList/1
// @include     https://live.bilibili.com/feed/getList/1
// @version     1.0.5.7
// @grant       none
// 
// @description 自动监听bilibili直播推送信息，当所关注者开启直播时自动打开直播网页的javascript脚本。
// ==/UserScript==
function main(){
    "use strict";
    
    var sAltAPI = '//api.live.bilibili.com/ajax/feed/list?pagesize=30&page=1';
    var running = true;
    var rProFilter, rConFilter;
    var rFilter = /./;
    var sMode = 'pro';
    var aTimer = [];
    var aAltRoomid = [];
    var sTitle = '';

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
        document.title = sTitle;
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
        sTitle = document.title;
        document.title = '已暂停';
    }
    function update(){
        try{
            var sCon = document.$('#con').value.trim();
            localStorage.bilinotify_con = sCon;
            rConFilter = new RegExp(sCon);
            var sPro = document.$('#pro').value.trim();
            localStorage.bilinotify_pro = sPro;
            rProFilter = new RegExp(sPro);
        } catch(e){console.log(e);}
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
        var style = document.createElement('style');
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
        var Obj = JSON.parse(document.body.childNodes[0].textContent.slice(1,-2));
        build();
        var Data = Obj.data;
        if(Obj.code == -101){
            document.body.insertAdjacentHTML('beforeend', '<br /><br />未登录');
            document.title = '未登录';
        }
        else if(Data.count>0) {
            document.title = "(！)有" + Data.count + "个直播";
            for(var x=0, item, sHTML; x<Data.count; x++){
                item = Data.list[x];
                //item.link = item.link.replace(/com\/(\d+)$/, 'com\/neptune\/$1');
                if (aAltRoomid != null && aAltRoomid.indexOf(item.roomid) == -1){
                    document.body.insertAdjacentHTML(
                        'beforeend',
                        'erroneous response from server'
                    );
                    document.title = '信息错误';
                    throw 'erroneous response from server';
                }
                sHTML = ([
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
                }));
                document.body.insertAdjacentHTML(
                    'beforeend', 
                    sHTML
                );
                checkopen(item);
            }
        }
        else{
            document.body.insertAdjacentHTML('beforeend', '<br /><br />无直播');
            document.title = "无直播";
        }
        sTitle = document.title;
        start();
        console.log('ended');
    }
    function handleAltList(sRes){
        var div = document.createElement('div');
        div.textContent = sRes;
        document.body.appendChild(div);
        var Obj = JSON.parse(sRes);
        if (Obj.code == 0){
            var aRooms = Obj.data.list;
            aRooms || (aRooms = []);
            for (var i=0; i<aRooms.length; i++){
                aAltRoomid.push(aRooms[i].roomid.toString());
            }
        }
        else{
            aAltRoomid = null;
        }
    }
    function getAltList(callback){
        var xhr = new XMLHttpRequest();
        xhr.timeout = 5000;
        var sRes = '';
        xhr.ontimeout = xhr.onerror = function(e){
            console.log('timeout when getting alternative list');
            setTimeout(function(){
                window.location.reload();
            }, 5000);

        };
        xhr.onload = function(e){
            try{
                sRes = xhr.response;
                callback(sRes);
            }catch(e){
                console.log(e.toString());
                setTimeout(function(){
                    window.location.reload();
                }, 30000);
            }
        }
        xhr.withCredentials = true;
        xhr.open('get', sAltAPI)
        xhr.send();
    }
    
    getAltList(function(sRes){
        if (sRes){
            handleAltList(sRes);
        }
        run();
    });
    //run();
}

try{
    main();
}catch(e){
    console.log(e.toString());
    setTimeout(function(){
        window.location.reload();
    }, 30000);
}
