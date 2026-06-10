import{_ as de,i as ce,a as ue,p as ve,r as z,q as fe,s as he,x as ge,c as ct,b as a,t as Lt,y as Nt,j as me,A as Dt,F as pe,E as ye,k as Bt,w as we,f as be,G as xe,B as jt,C as Ot,o as ut,z as Vt}from"./index-C7hJHkJE.js";import{u as Se}from"./data-CBk0Esc1.js";import{f as $,g as _t}from"./format-MwO7H02-.js";import{c as ke,S as Xt,C as Zt,u as Qt,a as _e,b as Me,d as Ce,e as $e,f as Te,Z as Fe,g as Ie,r as Ae,h as ze,l as Le,j as Ee,k as Re,m as Ut,n as De,i as nt}from"./index-BiBfcChI.js";function Ht(m,o){return o=o||{},ke(m,null,null,o.state!=="normal")}function Oe(m){var o=Xt.extend(m);return Xt.registerClass(o),o}function Pe(m){var o=Zt.extend(m);return Zt.registerClass(o),o}Qt([_e,Me]);Qt(Ce);Oe({type:"series.wordCloud",visualStyleAccessPath:"textStyle",visualStyleMapper:function(m){return{fill:m.get("color")}},visualDrawType:"fill",optionUpdated:function(){var m=this.option;m.gridSize=Math.max(Math.floor(m.gridSize),4)},getInitialData:function(m,o){var n=$e(m.data,{coordDimensions:["value"]}),u=new Te(n,this);return u.initData(m.data),u},defaultOption:{maskImage:null,shape:"circle",keepAspect:!1,left:"center",top:"center",width:"70%",height:"80%",sizeRange:[12,60],rotationRange:[-90,90],rotationStep:45,gridSize:8,drawOutOfBound:!1,shrinkToFit:!1,textStyle:{fontWeight:"normal"}}});Pe({type:"wordCloud",render:function(m,o,n){var u=this.group;u.removeAll();var i=m.getData(),b=m.get("gridSize");m.layoutInstance.ondraw=function(h,r,T,Y){var q=i.getItemModel(T),U=q.getModel("textStyle"),W=new Fe({style:Ht(U),scaleX:1/Y.info.mu,scaleY:1/Y.info.mu,x:(Y.gx+Y.info.gw/2)*b,y:(Y.gy+Y.info.gh/2)*b,rotation:Y.rot});W.setStyle({x:Y.info.fillTextOffsetX,y:Y.info.fillTextOffsetY+r*.5,text:h,verticalAlign:"middle",fill:i.getItemVisual(T,"style").fill,fontSize:r}),u.add(W),i.setItemGraphicEl(T,W),W.ensureState("emphasis").style=Ht(q.getModel(["emphasis","textStyle"]),{state:"emphasis"}),W.ensureState("blur").style=Ht(q.getModel(["blur","textStyle"]),{state:"blur"}),Ie(W,q.get(["emphasis","focus"]),q.get(["emphasis","blurScope"])),W.stateTransition={duration:m.get("animation")?m.get(["stateAnimation","duration"]):0,easing:m.get(["stateAnimation","easing"])},W.__highDownDispatcher=!0},this._model=m},remove:function(){this.group.removeAll(),this._model.layoutInstance.dispose()},dispose:function(){this._model.layoutInstance.dispose()}});/*!
 * wordcloud2.js
 * http://timdream.org/wordcloud2.js/
 *
 * Copyright 2011 - 2019 Tim Guan-tin Chien and contributors.
 * Released under the MIT license
 */window.setImmediate||(window.setImmediate=function(){return window.msSetImmediate||window.webkitSetImmediate||window.mozSetImmediate||window.oSetImmediate||function(){if(!window.postMessage||!window.addEventListener)return null;var n=[void 0],u="zero-timeout-message",i=function(h){var r=n.length;return n.push(h),window.postMessage(u+r.toString(36),"*"),r};return window.addEventListener("message",function(h){if(!(typeof h.data!="string"||h.data.substr(0,u.length)!==u)){h.stopImmediatePropagation();var r=parseInt(h.data.substr(u.length),36);n[r]&&(n[r](),n[r]=void 0)}},!0),window.clearImmediate=function(h){n[h]&&(n[h]=void 0)},i}()||function(n){window.setTimeout(n,0)}}());window.clearImmediate||(window.clearImmediate=function(){return window.msClearImmediate||window.webkitClearImmediate||window.mozClearImmediate||window.oClearImmediate||function(n){window.clearTimeout(n)}}());var Yt=function(){var o=document.createElement("canvas");if(!o||!o.getContext)return!1;var n=o.getContext("2d");return!(!n||!n.getImageData||!n.fillText||!Array.prototype.some||!Array.prototype.push)}(),Gt=function(){if(Yt){for(var o=document.createElement("canvas").getContext("2d"),n=20,u,i;n;){if(o.font=n.toString(10)+"px sans-serif",o.measureText("Ｗ").width===u&&o.measureText("m").width===i)return n+1;u=o.measureText("Ｗ").width,i=o.measureText("m").width,n--}return 0}}(),We=function(m){if(Array.isArray(m)){var o=m.slice();return o.splice(0,2),o}else return[]},Be=function(o){for(var n,u,i=o.length;i;)n=Math.floor(Math.random()*i),u=o[--i],o[i]=o[n],o[n]=u;return o},Mt={},Pt=function(o,n){if(!Yt)return;var u=Math.floor(Math.random()*Date.now());Array.isArray(o)||(o=[o]),o.forEach(function(p,s){if(typeof p=="string"){if(o[s]=document.getElementById(p),!o[s])throw new Error("The element id specified is not found.")}else if(!p.tagName&&!p.appendChild)throw new Error("You must pass valid HTML elements, or ID of the element.")});var i={list:[],fontFamily:'"Trebuchet MS", "Heiti TC", "微軟正黑體", "Arial Unicode MS", "Droid Fallback Sans", sans-serif',fontWeight:"normal",color:"random-dark",minSize:0,weightFactor:1,clearCanvas:!0,backgroundColor:"#fff",gridSize:8,drawOutOfBound:!1,shrinkToFit:!1,origin:null,drawMask:!1,maskColor:"rgba(255,0,0,0.3)",maskGapWidth:.3,layoutAnimation:!0,wait:0,abortThreshold:0,abort:function(){},minRotation:-Math.PI/2,maxRotation:Math.PI/2,rotationStep:.1,shuffle:!0,rotateRatio:.1,shape:"circle",ellipticity:.65,classes:null,hover:null,click:null};if(n)for(var b in n)b in i&&(i[b]=n[b]);if(typeof i.weightFactor!="function"){var h=i.weightFactor;i.weightFactor=function(s){return s*h}}if(typeof i.shape!="function")switch(i.shape){case"circle":default:i.shape="circle";break;case"cardioid":i.shape=function(s){return 1-Math.sin(s)};break;case"diamond":i.shape=function(s){var l=s%(2*Math.PI/4);return 1/(Math.cos(l)+Math.sin(l))};break;case"square":i.shape=function(s){return Math.min(1/Math.abs(Math.cos(s)),1/Math.abs(Math.sin(s)))};break;case"triangle-forward":i.shape=function(s){var l=s%(2*Math.PI/3);return 1/(Math.cos(l)+Math.sqrt(3)*Math.sin(l))};break;case"triangle":case"triangle-upright":i.shape=function(s){var l=(s+Math.PI*3/2)%(2*Math.PI/3);return 1/(Math.cos(l)+Math.sqrt(3)*Math.sin(l))};break;case"pentagon":i.shape=function(s){var l=(s+.955)%(2*Math.PI/5);return 1/(Math.cos(l)+.726543*Math.sin(l))};break;case"star":i.shape=function(s){var l=(s+.955)%(2*Math.PI/10);return(s+.955)%(2*Math.PI/5)-2*Math.PI/10>=0?1/(Math.cos(2*Math.PI/10-l)+3.07768*Math.sin(2*Math.PI/10-l)):1/(Math.cos(l)+3.07768*Math.sin(l))};break}i.gridSize=Math.max(Math.floor(i.gridSize),4);var r=i.gridSize,T=r-i.maskGapWidth,Y=Math.abs(i.maxRotation-i.minRotation),q=Math.min(i.maxRotation,i.minRotation),U=i.rotationStep,W,R,B,Q,H,j,it;function bt(p,s){return"hsl("+(Math.random()*360).toFixed()+","+(Math.random()*30+70).toFixed()+"%,"+(Math.random()*(s-p)+p).toFixed()+"%)"}switch(i.color){case"random-dark":it=function(){return bt(10,50)};break;case"random-light":it=function(){return bt(50,90)};break;default:typeof i.color=="function"&&(it=i.color);break}var ot;typeof i.fontWeight=="function"&&(ot=i.fontWeight);var gt=null;typeof i.classes=="function"&&(gt=i.classes);var mt=!1,vt=[],pt,xt=function(s){var l=s.currentTarget,c=l.getBoundingClientRect(),f,g;s.touches?(f=s.touches[0].clientX,g=s.touches[0].clientY):(f=s.clientX,g=s.clientY);var k=f-c.left,E=g-c.top,M=Math.floor(k*(l.width/c.width||1)/r),C=Math.floor(E*(l.height/c.height||1)/r);return vt[M]?vt[M][C]:null},St=function(s){var l=xt(s);if(pt!==l){if(pt=l,!l){i.hover(void 0,void 0,s);return}i.hover(l.item,l.dimension,s)}},yt=function(s){var l=xt(s);l&&(i.click(l.item,l.dimension,s),s.preventDefault())},ft=[],Ct=function(s){if(ft[s])return ft[s];var l=s*8,c=l,f=[];for(s===0&&f.push([Q[0],Q[1],0]);c--;){var g=1;i.shape!=="circle"&&(g=i.shape(c/l*2*Math.PI)),f.push([Q[0]+s*g*Math.cos(-c/l*2*Math.PI),Q[1]+s*g*Math.sin(-c/l*2*Math.PI)*i.ellipticity,c/l*2*Math.PI])}return ft[s]=f,f},wt=function(){return i.abortThreshold>0&&new Date().getTime()-j>i.abortThreshold},$t=function(){return i.rotateRatio===0||Math.random()>i.rotateRatio?0:Y===0?q:q+Math.round(Math.random()*Y/U)*U},Tt=function(s,l,c,f){var g=i.weightFactor(l);if(g<=i.minSize)return!1;var k=1;g<Gt&&(k=function(){for(var zt=2;zt*g<Gt;)zt+=2;return zt}());var E;ot?E=ot(s,l,g,f):E=i.fontWeight;var M=document.createElement("canvas"),C=M.getContext("2d",{willReadFrequently:!0});C.font=E+" "+(g*k).toString(10)+"px "+i.fontFamily;var O=C.measureText(s).width/k,F=Math.max(g*k,C.measureText("m").width,C.measureText("Ｗ").width)/k,I=O+F*2,D=F*3,N=Math.ceil(I/r),X=Math.ceil(D/r);I=N*r,D=X*r;var P=-O/2,_=-F*.4,A=Math.ceil((I*Math.abs(Math.sin(c))+D*Math.abs(Math.cos(c)))/r),G=Math.ceil((I*Math.abs(Math.cos(c))+D*Math.abs(Math.sin(c)))/r),Z=G*r,ht=A*r;M.setAttribute("width",Z),M.setAttribute("height",ht),C.scale(1/k,1/k),C.translate(Z*k/2,ht*k/2),C.rotate(-c),C.font=E+" "+(g*k).toString(10)+"px "+i.fontFamily,C.fillStyle="#000",C.textBaseline="middle",C.fillText(s,P*k,(_+g*.5)*k);var kt=C.getImageData(0,0,Z,ht).data;if(wt())return!1;for(var Et=[],lt=G,rt,It,At,at=[A/2,G/2,A/2,G/2];lt--;)for(rt=A;rt--;){At=r;t:for(;At--;)for(It=r;It--;)if(kt[((rt*r+At)*Z+(lt*r+It))*4+3]){Et.push([lt,rt]),lt<at[3]&&(at[3]=lt),lt>at[1]&&(at[1]=lt),rt<at[0]&&(at[0]=rt),rt>at[2]&&(at[2]=rt);break t}}return{mu:k,occupied:Et,bounds:at,gw:G,gh:A,fillTextOffsetX:P,fillTextOffsetY:_,fillTextWidth:O,fillTextHeight:F,fontSize:g}},Ft=function(s,l,c,f,g){for(var k=g.length;k--;){var E=s+g[k][0],M=l+g[k][1];if(E>=R||M>=B||E<0||M<0){if(!i.drawOutOfBound)return!1;continue}if(!W[E][M])return!1}return!0},st=function(s,l,c,f,g,k,E,M,C,O){var F=c.fontSize,I;it?I=it(f,g,F,k,E,O):I=i.color;var D;ot?D=ot(f,g,F,O):D=i.fontWeight;var N;gt?N=gt(f,g,F,O):N=i.classes,o.forEach(function(X){if(X.getContext){var P=X.getContext("2d"),_=c.mu;P.save(),P.scale(1/_,1/_),P.font=D+" "+(F*_).toString(10)+"px "+i.fontFamily,P.fillStyle=I,P.translate((s+c.gw/2)*r*_,(l+c.gh/2)*r*_),M!==0&&P.rotate(-M),P.textBaseline="middle",P.fillText(f,c.fillTextOffsetX*_,(c.fillTextOffsetY+F*.5)*_),P.restore()}else{var A=document.createElement("span"),G="";G="rotate("+-M/Math.PI*180+"deg) ",c.mu!==1&&(G+="translateX(-"+c.fillTextWidth/4+"px) scale("+1/c.mu+")");var Z={position:"absolute",display:"block",font:D+" "+F*c.mu+"px "+i.fontFamily,left:(s+c.gw/2)*r+c.fillTextOffsetX+"px",top:(l+c.gh/2)*r+c.fillTextOffsetY+"px",width:c.fillTextWidth+"px",height:c.fillTextHeight+"px",lineHeight:F+"px",whiteSpace:"nowrap",transform:G,webkitTransform:G,msTransform:G,transformOrigin:"50% 40%",webkitTransformOrigin:"50% 40%",msTransformOrigin:"50% 40%"};I&&(Z.color=I),A.textContent=f;for(var ht in Z)A.style[ht]=Z[ht];if(C)for(var kt in C)A.setAttribute(kt,C[kt]);N&&(A.className+=N),X.appendChild(A)}})},J=function(s,l,c,f,g){if(!(s>=R||l>=B||s<0||l<0)){if(W[s][l]=!1,c){var k=o[0].getContext("2d");k.fillRect(s*r,l*r,T,T)}mt&&(vt[s][l]={item:g,dimension:f})}},K=function(s,l,c,f,g,k){var E=g.occupied,M=i.drawMask,C;M&&(C=o[0].getContext("2d"),C.save(),C.fillStyle=i.maskColor);var O;if(mt){var F=g.bounds;O={x:(s+F[3])*r,y:(l+F[0])*r,w:(F[1]-F[3]+1)*r,h:(F[2]-F[0]+1)*r}}for(var I=E.length;I--;){var D=s+E[I][0],N=l+E[I][1];D>=R||N>=B||D<0||N<0||J(D,N,M,O,k)}M&&C.restore()},tt=function p(s,l){if(l>20)return null;var c,f,g;Array.isArray(s)?(c=s[0],f=s[1]):(c=s.word,f=s.weight,g=s.attributes);var k=$t(),E=We(s),M=Tt(c,f,k,E);if(!M||wt())return!1;if(!i.drawOutOfBound&&!i.shrinkToFit){var C=M.bounds;if(C[1]-C[3]+1>R||C[2]-C[0]+1>B)return!1}for(var O=H+1,F=function(X){var P=Math.floor(X[0]-M.gw/2),_=Math.floor(X[1]-M.gh/2),A=M.gw,G=M.gh;return Ft(P,_,A,G,M.occupied)?(st(P,_,M,c,f,H-O,X[2],k,g,E),K(P,_,A,G,M,s),{gx:P,gy:_,rot:k,info:M}):!1};O--;){var I=Ct(H-O);i.shuffle&&(I=[].concat(I),Be(I));for(var D=0;D<I.length;D++){var N=F(I[D]);if(N)return N}}return i.shrinkToFit?(Array.isArray(s)?s[1]=s[1]*3/4:s.weight=s.weight*3/4,p(s,l+1)):null},V=function(s,l,c){if(l)return!o.some(function(f){var g=new CustomEvent(s,{detail:c||{}});return!f.dispatchEvent(g)},this);o.forEach(function(f){var g=new CustomEvent(s,{detail:c||{}});f.dispatchEvent(g)},this)},et=function(){var s=o[0];if(s.getContext)R=Math.ceil(s.width/r),B=Math.ceil(s.height/r);else{var l=s.getBoundingClientRect();R=Math.ceil(l.width/r),B=Math.ceil(l.height/r)}if(V("wordcloudstart",!0)){Q=i.origin?[i.origin[0]/r,i.origin[1]/r]:[R/2,B/2],H=Math.floor(Math.sqrt(R*R+B*B)),W=[];var c,f,g;if(!s.getContext||i.clearCanvas)for(o.forEach(function(_){if(_.getContext){var A=_.getContext("2d");A.fillStyle=i.backgroundColor,A.clearRect(0,0,R*(r+1),B*(r+1)),A.fillRect(0,0,R*(r+1),B*(r+1))}else _.textContent="",_.style.backgroundColor=i.backgroundColor,_.style.position="relative"}),c=R;c--;)for(W[c]=[],f=B;f--;)W[c][f]=!0;else{var k=document.createElement("canvas").getContext("2d");k.fillStyle=i.backgroundColor,k.fillRect(0,0,1,1);var E=k.getImageData(0,0,1,1).data,M=s.getContext("2d").getImageData(0,0,R*r,B*r).data;c=R;for(var C,O;c--;)for(W[c]=[],f=B;f--;){O=r;t:for(;O--;)for(C=r;C--;)for(g=4;g--;)if(M[((f*r+O)*R*r+(c*r+C))*4+g]!==E[g]){W[c][f]=!1;break t}W[c][f]!==!1&&(W[c][f]=!0)}M=k=E=void 0}if(i.hover||i.click){for(mt=!0,c=R+1;c--;)vt[c]=[];i.hover&&s.addEventListener("mousemove",St),i.click&&(s.addEventListener("click",yt),s.addEventListener("touchstart",yt),s.addEventListener("touchend",function(_){_.preventDefault()}),s.style.webkitTapHighlightColor="rgba(0, 0, 0, 0)"),s.addEventListener("wordcloudstart",function _(){s.removeEventListener("wordcloudstart",_),s.removeEventListener("mousemove",St),s.removeEventListener("click",yt),pt=void 0})}g=0;var F,I,D=!0;i.layoutAnimation?i.wait!==0?(F=window.setTimeout,I=window.clearTimeout):(F=window.setImmediate,I=window.clearImmediate):(F=function(_){_()},I=function(){D=!1});var N=function(A,G){o.forEach(function(Z){Z.addEventListener(A,G)},this)},X=function(A,G){o.forEach(function(Z){Z.removeEventListener(A,G)},this)},P=function _(){X("wordcloudstart",_),I(Mt[u])};N("wordcloudstart",P),Mt[u]=(i.layoutAnimation?F:setTimeout)(function _(){if(D){if(g>=i.list.length){I(Mt[u]),V("wordcloudstop",!1),X("wordcloudstart",P),delete Mt[u];return}j=new Date().getTime();var A=tt(i.list[g],0),G=!V("wordclouddrawn",!0,{item:i.list[g],drawn:A});if(wt()||G){I(Mt[u]),i.abort(),V("wordcloudabort",!1),V("wordcloudstop",!1),X("wordcloudstart",P);return}g++,Mt[u]=F(_,i.wait)}},i.wait)}};et()};Pt.isSupported=Yt;Pt.minFontSize=Gt;if(!Pt.isSupported)throw new Error("Sorry your browser not support wordCloud");function He(m){for(var o=m.getContext("2d"),n=o.getImageData(0,0,m.width,m.height),u=o.createImageData(n),i=0,b=0,h=0;h<n.data.length;h+=4){var r=n.data[h+3];if(r>128){var T=n.data[h]+n.data[h+1]+n.data[h+2];i+=T,++b}}for(var Y=i/b,h=0;h<n.data.length;h+=4){var T=n.data[h]+n.data[h+1]+n.data[h+2],r=n.data[h+3];r<128||T>Y?(u.data[h]=0,u.data[h+1]=0,u.data[h+2]=0,u.data[h+3]=0):(u.data[h]=255,u.data[h+1]=255,u.data[h+2]=255,u.data[h+3]=255)}o.putImageData(u,0,0)}Ae(function(m,o){m.eachSeriesByType("wordCloud",function(n){var u=ze(n.getBoxLayoutParams(),{width:o.getWidth(),height:o.getHeight()}),i=n.get("keepAspect"),b=n.get("maskImage"),h=b?b.width/b.height:1;i&&Ge(u,h);var r=n.getData(),T=document.createElement("canvas");T.width=u.width,T.height=u.height;var Y=T.getContext("2d");if(b)try{Y.drawImage(b,0,0,T.width,T.height),He(T)}catch(H){console.error("Invalid mask image"),console.error(H.toString())}var q=n.get("sizeRange"),U=n.get("rotationRange"),W=r.getDataExtent("value"),R=Math.PI/180,B=n.get("gridSize");Pt(T,{list:r.mapArray("value",function(H,j){var it=r.getItemModel(j);return[r.getName(j),it.get("textStyle.fontSize",!0)||Le(H,W,q),j]}).sort(function(H,j){return j[1]-H[1]}),fontFamily:n.get("textStyle.fontFamily")||n.get("emphasis.textStyle.fontFamily")||m.get("textStyle.fontFamily"),fontWeight:n.get("textStyle.fontWeight")||n.get("emphasis.textStyle.fontWeight")||m.get("textStyle.fontWeight"),gridSize:B,ellipticity:u.height/u.width,minRotation:U[0]*R,maxRotation:U[1]*R,clearCanvas:!b,rotateRatio:1,rotationStep:n.get("rotationStep")*R,drawOutOfBound:n.get("drawOutOfBound"),shrinkToFit:n.get("shrinkToFit"),layoutAnimation:n.get("layoutAnimation"),shuffle:!1,shape:n.get("shape")});function Q(H){var j=H.detail.item;H.detail.drawn&&n.layoutInstance.ondraw&&(H.detail.drawn.gx+=u.x/B,H.detail.drawn.gy+=u.y/B,n.layoutInstance.ondraw(j[0],j[1],j[2],H.detail.drawn))}T.addEventListener("wordclouddrawn",Q),n.layoutInstance&&n.layoutInstance.dispose(),n.layoutInstance={ondraw:null,dispose:function(){T.removeEventListener("wordclouddrawn",Q),T.addEventListener("wordclouddrawn",function(H){H.preventDefault()})}}})});Ee(function(m){var o=(m||{}).series;!Re(o)&&(o=o?[o]:[]);var n=["shadowColor","shadowBlur","shadowOffsetX","shadowOffsetY"];Ut(o,function(i){if(i&&i.type==="wordCloud"){var b=i.textStyle||{};u(b.normal),u(b.emphasis)}});function u(i){i&&Ut(n,function(b){i.hasOwnProperty(b)&&(i["text"+De(b)]=i[b])})}});function Ge(m,o){var n=m.width,u=m.height;n>u*o?(m.x+=(n-u*o)/2,m.width=u*o):(m.y+=(u-n/o)/2,m.height=n/o)}const Ye={class:"insights-page"},qe={class:"page-header"},Ne={class:"control-group"},je=["disabled"],Ve={class:"control-display"},Xe=["disabled"],Ze={key:0,class:"page-loading"},Ue={key:1,class:"insights-content"},Qe={class:"top-analysis-section"},Je={class:"analysis-card sankey-card"},Ke={class:"core-analysis-grid"},ta={class:"analysis-card profile-card"},ea={class:"analysis-card merchant-list-card"},aa={class:"card-content"},ia={class:"analysis-card scenario-card"},sa={class:"card-content"},na={class:"scenario-tabs"},ra={class:"analysis-card bankcard-card"},oa={class:"card-content"},la={key:0,class:"bankcard-list"},da={class:"bank-meta"},ca={class:"bank-name"},ua={class:"bank-bar-wrap"},va={class:"bank-amt"},fa={class:"bank-money"},ha={class:"bank-count"},ga={key:1,class:"empty-hint"},ma={class:"analysis-card habit-card"},pa={class:"card-content"},ya={class:"advanced-insights-grid"},wa={class:"analysis-card insight-card latte-card"},ba={class:"analysis-card insight-card sub-card"},xa={class:"analysis-card insight-card inflation-card"},Sa={class:"analysis-card insight-card loyalty-card"},ka={class:"analysis-card insight-card weekend-card"},_a={class:"advanced-viz-section"},Ma={class:"analysis-card full-width-viz-card"},Ca={class:"viz-row"},$a={class:"analysis-card"},Ta={class:"analysis-card"},Fa={class:"analysis-card full-width-viz-card",style:{height:"600px"}},Ia={class:"viz-row"},Aa={class:"analysis-card"},za={class:"analysis-card"},La={class:"analysis-card full-width-viz-card"},Ea={class:"viz-row"},Ra={class:"analysis-card"},Da={class:"analysis-card"},Oa={key:2,class:"empty-state"},Pa={class:"story-content"},Wa={class:"story-controls"},Ba={__name:"Insights",setup(m){const o=Se(),n=ce(),u=ue(),i=ve(),b=z(new Date().getFullYear()),h=z([]),r=z(null),T=z("channel"),Y=z(!1),q=z(0),U=Ot(()=>r.value&&r.value.bank_card_analysis||[]),W=t=>{const e=U.value.length?U.value[0].amount:0;return e>0?Math.max(3,t.amount/e*100):0},R=z(null),B=z(null),Q=z(null),H=z(null),j=z(null),it=z(null),bt=z(null),ot=z(null),gt=z(null),mt=z(null),vt=z(null),pt=z(null),xt=z(null),St=z(null),yt=z(null),ft=z(null),Ct=z(null),wt=z(null),$t=z(null),Tt=z(null),Ft=z(null);let st=null,J=null,K=null,tt=null,V=null,et=null,p=null,s=null,l=null,c=null,f=null;const g=Ot(()=>h.value.indexOf(b.value)<h.value.length-1),k=Ot(()=>h.value.indexOf(b.value)>0),E=Ot(()=>{var t;return((t=r.value)==null?void 0:t.story_data)||[]});function M(){const t=h.value.indexOf(b.value);t<h.value.length-1&&(b.value=h.value[t+1],A(b.value))}function C(){const t=h.value.indexOf(b.value);t>0&&(b.value=h.value[t-1],A(b.value))}function O(t){T.value=t,at()}function F(){q.value>0&&(q.value--,D())}function I(){q.value<X-1&&(q.value++,D())}function D(){const t=Tt.value;t&&(t.querySelectorAll(".slide").forEach((d,x)=>{d.classList.toggle("active",x===q.value)}),N())}function N(){const t=Ft.value;t&&Array.from(t.children).forEach((e,d)=>{e.classList.toggle("active",d===q.value)})}let X=0;async function P(){if(!E.value){console.warn("[Story] No story data available");return}q.value=0,Y.value=!0,await jt(),_()}function _(){const t=E.value;if(console.log("[Story] generateStorySlides called, data:",t),!t){console.warn("[Story] No data available");return}const e=Tt.value,d=Ft.value;if(console.log("[Story] slides element:",e),console.log("[Story] indicators element:",d),!e||!d){console.warn("[Story] DOM elements not found");return}const x=[`
    <div class="slide active">
      <div class="slide-content">
        <h1>您的年度消费故事</h1>
        <p>这一年，您经历了 ${t.summary.total_days} 个日夜</p>
        <p>完成了 ${t.summary.tx_count} 笔交易</p>
        <div class="slide-big-icon"><i class="fas fa-book-open"></i></div>
      </div>
    </div>
    `,t.features&&t.features.first_tx?`
    <div class="slide">
      <div class="slide-content">
        <h2>🎬 故事的开始</h2>
        <div class="slide-date">${t.features.first_tx.date}</div>
        <p>您在 <strong>${t.features.first_tx.merchant}</strong></p>
        <div class="slide-amount">¥${$(t.features.first_tx.amount)}</div>
        <p>用这笔消费开启了全新的一年。</p>
        <div class="slide-big-icon"><i class="fas fa-play-circle"></i></div>
      </div>
    </div>
    `:"",t.features&&t.features.peak_hour!==void 0?`
    <div class="slide">
      <div class="slide-content">
        <h2>⏰ 剁手黄金点</h2>
        <p>每天的 <strong>${t.features.peak_hour}点</strong></p>
        <div class="slide-keyword" style="font-size:32px">是您最活跃的时刻</div>
        <p>${t.features.peak_hour<12?"早起的鸟儿有虫吃？":t.features.peak_hour>20?"月黑风高夜，正是剁手时。":"工作日摸鱼下单？"}</p>
        <div class="slide-big-icon"><i class="fas fa-clock"></i></div>
      </div>
    </div>
    `:"",t.features&&t.features.takeout&&t.features.takeout.count>5?`
    <div class="slide">
      <div class="slide-content">
        <h2>🥡 外卖品鉴家</h2>
        <div class="slide-amount">${t.features.takeout.count} 单</div>
        <p>贡献了 ${$(t.features.takeout.amount)} 元给外卖/快餐</p>
        <p>世界那么大，还是外卖最懂你的胃。</p>
        <div class="slide-big-icon"><i class="fas fa-utensils"></i></div>
      </div>
    </div>
    `:"",t.features&&t.features.top_season?`
    <div class="slide">
      <div class="slide-content">
        <h2>🍂 季节限定记忆</h2>
        <p>您在</p>
        <div class="slide-keyword" style="color:#FF7950">${t.features.top_season}天</div>
        <p>留下了最多的消费足迹。</p>
        <div class="slide-big-icon"><i class="fas ${t.features.top_season==="冬"?"fa-snowflake":t.features.top_season==="夏"?"fa-sun":"fa-leaf"}"></i></div>
      </div>
    </div>
    `:"",t.features&&t.features.coffee&&t.features.coffee.count>0?`
    <div class="slide">
      <div class="slide-content">
        <h2>☕️ 续命指数</h2>
        <div class="slide-amount">${t.features.coffee.count} 杯</div>
        <p>您今年在咖啡/奶茶上投入了</p>
        <div class="slide-keyword" style="font-size:24px">¥${$(t.features.coffee.amount)}</div>
        <p>${t.features.coffee.count>100?"相当于喝掉了一个浴缸的量！":"您是理性的咖啡因摄入者。"}</p>
        <div class="slide-big-icon"><i class="fas fa-coffee"></i></div>
      </div>
    </div>
    `:"",t.features&&t.features.night&&t.features.night.count>0?`
    <div class="slide">
      <div class="slide-content">
        <h2>🌙 深夜哲学</h2>
        <p>晚10点后，您平均消费</p>
        <div class="slide-amount">¥${$(t.features.night.avg)}</div>
        <p>看来深夜不仅有灵感，还有食欲。</p>
        <div class="slide-big-icon"><i class="fas fa-moon"></i></div>
      </div>
    </div>
    `:"",t.features&&t.features.weekend?`
    <div class="slide">
      <div class="slide-content">
        <h2>🎭 周末人格</h2>
        <p>工作日均价 vs 周末均价</p>
        <div class="slide-amount" style="font-size:32px">¥${$(t.features.weekend.weekday_avg)} <span style="font-size:20px;color:#999">vs</span> ¥${$(t.features.weekend.weekend_avg)}</div>
        <p>${t.features.weekend.weekend_avg>t.features.weekend.weekday_avg*2?"平日沙县小吃，周末米其林大餐！":"您的消费习惯非常稳定。"}</p>
        <div class="slide-big-icon"><i class="fas fa-mask"></i></div>
      </div>
    </div>
    `:"",t.features&&t.features.inflation&&t.features.inflation.trend!=="stable"?`
    <div class="slide">
      <div class="slide-content">
        <h2>📈 通胀感知</h2>
        <p>您常去的 <strong>${t.features.inflation.merchant}</strong></p>
        <div class="slide-amount" style="font-size:32px">¥${$(t.features.inflation.start_price)} ➔ ¥${$(t.features.inflation.end_price)}</div>
        <p>${t.features.inflation.trend==="up"?"悄悄涨价了，且喝且珍惜。":"居然降价了？良心商家！"}</p>
        <div class="slide-big-icon"><i class="fas fa-chart-line"></i></div>
      </div>
    </div>
    `:"",`
    <div class="slide">
      <div class="slide-content">
        <h2>💸 最"壕"的一天</h2>
        <div class="slide-date">${t.max_day.date}</div>
        <div class="slide-amount">${$(t.max_day.amount)}</div>
        <p>那天发生了什么？是爱自己多一点吗？</p>
        <div class="slide-big-icon"><i class="fas fa-shopping-bag"></i></div>
      </div>
    </div>
    `,`
    <div class="slide">
      <div class="slide-content">
        <h2>✨ 年度关键词</h2>
        <div class="slide-keyword">${t.top_category.name}</div>
        <p>这是您投入最多的领域 (${$(t.top_category.amount)})</p>
        <p>新的一年，愿每一笔消费都物超所值！</p>
        <div class="slide-big-icon"><i class="fas fa-star"></i></div>
      </div>
    </div>
    `].filter(Boolean);X=x.length,e.innerHTML=x.join(""),d.innerHTML=x.map((v,S)=>`<span class="indicator ${S===0?"active":""}" data-slide-index="${S}"></span>`).join(""),D()}async function A(t){try{console.log("[Insights] Loading data for year:",t,"filter:",i.currentFilter),n.setGlobalLoading(!0);const e={year:t,...i.getFilterParams()},d=await xe.getAnalysis(e);console.log("[Insights] Data loaded:",d),r.value=d,await jt(),G(),ht()}catch(e){console.error("[Insights] Failed to load data:",e),n.showError("加载数据失败: "+e.message)}finally{n.setGlobalLoading(!1)}}function G(){B.value&&(st=nt(B.value)),Q.value&&(J=nt(Q.value)),H.value&&(K=nt(H.value)),j.value&&(tt=nt(j.value)),it.value&&(V=nt(it.value)),bt.value&&(et=nt(bt.value)),ot.value&&(p=nt(ot.value)),gt.value&&(s=nt(gt.value)),mt.value&&(l=nt(mt.value)),vt.value&&(c=nt(vt.value)),R.value&&(f=nt(R.value)),at(),Jt(),window.addEventListener("resize",Z)}function Z(){st==null||st.resize(),J==null||J.resize(),K==null||K.resize(),tt==null||tt.resize(),V==null||V.resize(),et==null||et.resize(),p==null||p.resize(),s==null||s.resize(),l==null||l.resize(),c==null||c.resize(),f==null||f.resize()}function ht(){kt(),At(),qt(),zt()}function kt(){const t=r.value;if(!t||!pt.value)return;const e=t.tags||{},x=`
    <div class="tag-cloud">
      ${(e.tags||[]).map(S=>`<span class="tag">${S}</span>`).join("")}
    </div>
  `,v=`
    <div class="profile-details">
      <div class="profile-feature">
        <div class="feature-icon"><i class="fas fa-clock"></i></div>
        <div class="feature-content">
          <div class="feature-title">消费时间</div>
          <div class="feature-description">${Et(e.time_pattern||"-")}</div>
        </div>
      </div>
      <div class="profile-feature">
        <div class="feature-icon"><i class="fas fa-shopping-bag"></i></div>
        <div class="feature-content">
          <div class="feature-title">消费偏好</div>
          <div class="feature-description">${lt(e.spending_preference||"-")}</div>
        </div>
      </div>
      <div class="profile-feature">
        <div class="feature-icon"><i class="fas fa-chart-line"></i></div>
        <div class="feature-content">
          <div class="feature-title">消费规律</div>
          <div class="feature-description">${rt(e.spending_pattern||"-")}</div>
        </div>
      </div>
      <div class="profile-feature">
        <div class="feature-icon"><i class="fas fa-wallet"></i></div>
        <div class="feature-content">
          <div class="feature-title">消费能力</div>
          <div class="feature-description">${It(e.spending_power||"-")}</div>
        </div>
      </div>
    </div>
  `;pt.value.innerHTML=x+v}function Et(t){return t==="-"?t:t.replace(/(夜间|早起|日间)/g,'<span class="highlight">$1</span>')}function lt(t){return t==="-"?t:t.replace(/最常消费的品类是/,"").replace(/([^，。]+?)(\([0-9.]+%\))/g,'<span class="highlight">$1</span><span class="percentage">$2</span>')}function rt(t){return t==="-"?t:t.replace(/(非常有规律|理性|较为均衡|比较随性)/g,'<span class="highlight">$1</span>')}function It(t){return t==="-"?t:t.replace(/日均消费([0-9]+)元/g,'日均消费<span class="amount">$1</span>元').replace(/，属于(高|中等|理性)消费人群/g,'，属于<span class="highlight">$1</span>消费人群')}function At(){var d;const t=r.value;if(!t||!xt.value)return;const e=((d=t.merchant_analysis)==null?void 0:d.frequent_merchants)||[];xt.value.innerHTML=e.map((x,v)=>`
    <div class="merchant-item ${v<3?"top-"+(v+1):""}">
      <div class="merchant-info">
        <div class="merchant-rank">${v+1}</div>
        <div class="merchant-details">
          <div class="merchant-name">${x.name}</div>
          <div class="merchant-meta">上次消费: ${x.last_visit||"-"}</div>
        </div>
      </div>
      <div class="merchant-stats">
        <div class="stat-group">
          <div class="label">消费金额</div>
          <div class="value">${$(x.amount)}</div>
        </div>
        <div class="stat-group">
          <div class="label">消费次数</div>
          <div class="value">${x.count}次</div>
        </div>
      </div>
    </div>
  `).join("")}function at(){if(!st||!r.value)return;const t=r.value.scenario_analysis||[],e=r.value.payment_analysis||[],x={channel:t.filter(y=>y.category==="渠道"),time:t.filter(y=>y.category==="时段"),amount:t.filter(y=>y.category==="层级"),payment:e.map(y=>({name:y.name,value:y.total_amount}))}[T.value]||[],v=x.reduce((y,L)=>y+(L.value||0),0),S={channel:["#007AFF","#5856D6"],time:["#FF9500","#FF3B30","#34C759","#5856D6","#007AFF","#FF2D55"],amount:["#FF3B30","#FF9500","#34C759","#007AFF"],payment:["#007AFF","#FF9500","#34C759","#5856D6","#FF3B30","#FF2D55","#64D2FF"]},w={tooltip:{trigger:"item",formatter:y=>{const L=(y.value/v*100).toFixed(2);return`${y.name}<br/>金额：${$(y.value)}元<br/>占比：${L}%`}},series:[{name:"金额分布",type:"pie",radius:["25%","60%"],center:["50%","50%"],avoidLabelOverlap:!0,itemStyle:{borderRadius:5,borderColor:"#fff",borderWidth:2},label:{show:!0,position:"outside",formatter:y=>{const L=(y.value/v*100).toFixed(2);return L>1?`${y.name}
${L}%`:""},fontSize:12,color:"#666",lineHeight:16},labelLine:{show:y=>y.value/v*100>1,length:8,length2:8,smooth:!0,maxSurfaceAngle:80},data:x.map((y,L)=>({name:y.name,value:y.value,itemStyle:{color:S[T.value][L%S[T.value].length]}}))}]};st.setOption(w,!0)}function qt(){var v,S,w;const t=r.value;if(!t||!St.value)return;const e=t.habit_analysis||{},d=t.nighttime_analysis||{},x=t.engel_coefficient||{};St.value.innerHTML=`
    <div class="stat-item">
      <div class="stat-value">${((v=e.daily_avg)==null?void 0:v.toFixed(2))||0}</div>
      <div class="stat-label">日均消费(元)</div>
    </div>
    <div class="stat-item">
      <div class="stat-value">${e.weekend_ratio||0}%</div>
      <div class="stat-label">周末消费占比</div>
    </div>
    <div class="stat-item">
      <div class="stat-value">${e.fixed_expenses||0}%</div>
      <div class="stat-label">固定支出占比</div>
    </div>
    <div class="stat-item">
      <div class="stat-value">${e.month_start_ratio||0}%</div>
      <div class="stat-label">月初消费占比</div>
    </div>
    <div class="stat-item">
      <div class="stat-value">${((S=d.ratio)==null?void 0:S.toFixed(2))||0}%</div>
      <div class="stat-label">深夜剁手</div>
    </div>
    <div class="stat-item">
      <div class="stat-value">${((w=x.ratio)==null?void 0:w.toFixed(2))||0}%</div>
      <div class="stat-label">恩格尔系数</div>
    </div>
  `}function zt(){var w;const t=r.value;if(!t)return;const e=t.latte_factor||{};yt.value&&(yt.value.innerHTML=`
      <div class="insight-stat-big">${$(e.total_amount||0)}</div>
      <div class="insight-desc">累计在 <span class="highlight">${e.top_merchant||"-"}</span> 等小额消费上花费</div>
      <div class="insight-meta">相当于 ${Math.floor((e.total_amount||0)/30)} 杯咖啡</div>
    `);const d=t.subscription_analysis||[];if(ft.value)if(d.length>0){const y=d.reduce((L,dt)=>L+(dt.annual_amount||0),0);ft.value.innerHTML=`
        <div class="insight-stat-big">${$(y)}</div>
        <div class="insight-desc">预估年化订阅总支出</div>
        <div class="insight-list">
          ${d.slice(0,2).map(L=>`
            <div class="insight-item">
              <span>${L.name}</span>
              <span>${$(L.monthly_amount)}/月</span>
            </div>
          `).join("")}
        </div>
      `}else ft.value.innerHTML='<div class="empty-state">未发现明显订阅支出</div>';const x=t.inflation_analysis||{};if(Ct.value){const y=x.trend==="up"?"fa-arrow-up":x.trend==="down"?"fa-arrow-down":"fa-minus",L=x.trend==="up"?"#FF3B30":x.trend==="down"?"#34C759":"#8E8E93";Ct.value.innerHTML=`
      <div class="insight-stat-big" style="color: ${L}">
        <i class="fas ${y}"></i> ${Math.abs(x.rate||0).toFixed(2)}%
      </div>
      <div class="insight-desc">季度客单价变化趋势</div>
      <div class="insight-meta">从 ${$(x.first_avg||0)} 变动至 ${$(x.last_avg||0)}</div>
    `}const v=t.brand_loyalty||{};wt.value&&v.top_amount&&(wt.value.innerHTML=`
      <div class="loyalty-row">
        <div class="loyalty-item">
          <div class="loyalty-value">${v.top_amount.name||"-"}</div>
          <div class="loyalty-details">
            <span class="loyalty-amount">${$(v.top_amount.value||0)}</span>
            <span class="loyalty-tag">真金白银</span>
          </div>
        </div>
        <div class="loyalty-item">
          <div class="loyalty-value">${((w=v.top_count)==null?void 0:w.name)||"-"}</div>
          <div class="loyalty-details">
            <span class="loyalty-amount">${v.top_count.value||0}次</span>
            <span class="loyalty-tag">最为长情</span>
          </div>
        </div>
      </div>
    `);const S=t.weekend_monday||{};if($t.value){const y=S.ratio||0;let L="平稳型";y>1.5?L="周末狂欢型":y<.8&&(L="周一补偿型"),$t.value.innerHTML=`
      <div class="insight-stat-big">${y.toFixed(2)}x</div>
      <div class="insight-desc">周末日均消费是周一的倍数</div>
      <div class="insight-meta">类型: ${L}</div>
    `}}function Jt(){const t=r.value;t&&(t.sankey_data&&f&&Kt(t.sankey_data),t.themeriver_data&&J&&te(t.themeriver_data),t.boxplot_data&&c&&le(t.boxplot_data),t.heatmap_data&&K&&ee(t.heatmap_data),t.pareto_data&&s&&re(t.pareto_data),t.chord_data&&et&&se(t.chord_data),t.quadrant_data&&V&&ie(t.quadrant_data),t.funnel_data&&p&&ne(t.funnel_data),t.radar_data&&tt&&ae(t.radar_data),t.wordcloud_data&&l&&oe(t.wordcloud_data))}function Kt(t){if(!f||!t.nodes||t.nodes.length===0)return;const e={tooltip:{trigger:"item",triggerOn:"mousemove",formatter:function(d){return d.dataType==="edge"?`${d.data.source} > ${d.data.target}<br/>金额: ${$(d.data.value)} 元`:`${d.name}<br/>金额: ${$(d.data.value||d.value)} 元`}},series:[{type:"sankey",layoutIterations:0,nodeGap:12,data:t.nodes,links:t.links,emphasis:{focus:"adjacency"},lineStyle:{color:"gradient",curveness:.5},label:{color:"rgba(0,0,0,0.7)",fontFamily:"Arial"}}]};f.setOption(e,!0)}function te(t){if(!J||!t.data||t.data.length===0)return;const e=t.data.map(v=>[v[0],v[2],v[1]]),x={color:t.categories.map(v=>_t(v)),tooltip:{trigger:"axis",axisPointer:{type:"line",lineStyle:{color:"rgba(0,0,0,0.2)",width:1,type:"solid"}},formatter:v=>{if(!v||v.length===0)return"";const S=new Date(v[0].axisValue);let y='<div style="font-weight:bold;margin-bottom:5px;">'+(S.getFullYear()+"-"+(S.getMonth()+1).toString().padStart(2,"0"))+"</div>";return[...v].sort((dt,Rt)=>Rt.value[1]-dt.value[1]).forEach(dt=>{const Rt=dt.value[2],Wt=dt.value[1];y+='<div style="display:flex;justify-content:space-between;align-items:center;min-width:150px;"><span>'+dt.marker+" "+Rt+'</span><span style="font-weight:bold;margin-left:15px;">¥'+$(Wt)+"</span></div>"}),y}},legend:{data:t.categories,top:10,textStyle:{fontSize:12}},singleAxis:{top:50,bottom:50,axisTick:{},axisLabel:{},type:"time",axisPointer:{animation:!0,label:{show:!0}},splitLine:{show:!0,lineStyle:{type:"dashed",opacity:.2}}},series:[{type:"themeRiver",emphasis:{itemStyle:{shadowBlur:20,shadowColor:"rgba(0, 0, 0, 0.8)"}},data:e}]};J.setOption(x,!0)}function ee(t){if(!K||!t||t.length===0)return;const e=Array.from({length:24},(S,w)=>w+"点"),d=["周一","周二","周三","周四","周五","周六","周日"],x=Math.max(...t.map(S=>S[2])),v={tooltip:{position:"top",formatter:S=>`${d[S.value[1]]} ${e[S.value[0]]}<br />消费频次: ${S.value[2]}`},grid:{height:"50%",top:"10%",left:"15%"},xAxis:{type:"category",data:e,splitArea:{show:!0},axisLabel:{interval:2}},yAxis:{type:"category",data:d,splitArea:{show:!0}},visualMap:{min:0,max:x,calculable:!0,orient:"horizontal",left:"center",bottom:"0%",inRange:{color:["#f0f9ff","#bae6fd","#0ea5e9","#0284c7"]}},series:[{name:"Punch Card",type:"heatmap",data:t,label:{show:!1},emphasis:{itemStyle:{shadowBlur:10,shadowColor:"rgba(0, 0, 0, 0.5)"}}}]};K.setOption(v,!0)}function ae(t){if(!tt||!t.indicator||t.indicator.length===0)return;const e={tooltip:{trigger:"item",formatter:d=>{let x=d.name+"<br/>";return t.indicator.forEach((v,S)=>{x+=v.name+": ¥"+$(d.value[S])+"<br/>"}),x}},legend:{data:t.series.map(d=>d.name),top:10},radar:{indicator:t.indicator,radius:"65%"},series:[{name:"季度消费结构",type:"radar",data:t.series}]};tt.setOption(e,!0)}function ie(t){if(!V||!t||t.length===0)return;const e=t.reduce((v,S)=>v+(S.frequency||0),0)/t.length,d=t.reduce((v,S)=>v+(S.avg_amount||0),0)/t.length,x={tooltip:{formatter:v=>{const S=v.data;return`
          <div style="font-weight:bold;margin-bottom:5px;">${S.name}</div>
          分类：${S.category}<br/>
          频次：${S.frequency} 次<br/>
          均价：¥${$(S.avg_amount)}<br/>
          总额：¥${$(S.total_amount)}
        `}},grid:{left:"5%",right:"10%",bottom:"10%",top:"10%",containLabel:!0},xAxis:{name:"消费频次 (次)",type:"log",logBase:2,splitLine:{lineStyle:{type:"dashed"}}},yAxis:{name:"单笔均价 (元)",type:"log",logBase:2,splitLine:{lineStyle:{type:"dashed"}}},series:[{type:"scatter",data:t.map(v=>({...v,value:[v.frequency,v.avg_amount],symbolSize:Math.max(10,Math.min(Math.log(v.total_amount||1)*5,60)),itemStyle:{color:_t(v.category),shadowBlur:10,shadowColor:"rgba(0, 0, 0, 0.2)"}})),markLine:{silent:!0,lineStyle:{color:"#999",type:"solid",width:1},data:[{xAxis:e,name:"平均频次"},{yAxis:d,name:"平均均价"}]}}]};V.setOption(x,!0)}function se(t){if(!et||!t.nodes||t.nodes.length===0)return;let e=0,d=1/0;t.links.forEach(w=>{e=Math.max(e,w.value||0),d=Math.min(d,w.value||0)});const x=t.nodes.map(w=>({...w,itemStyle:{color:_t(w.name)}})),v=(t.links||[]).map(w=>{let y=1;return e>d&&(y=1+((w.value||0)-d)/(e-d)*7),{...w,lineStyle:{width:y,color:_t(w.target),curveness:.3,opacity:.7},emphasis:{lineStyle:{width:y+3,opacity:1}}}}),S={tooltip:{formatter:w=>w.dataType==="edge"?w.data.source+" -> "+w.data.target+"<br/>消费金额: ¥"+$(w.data.value):w.name},series:[{type:"graph",layout:"circular",circular:{rotateLabel:!0},data:x,links:v,roam:!1,zoom:.75,label:{show:!0,position:"right",formatter:"{b}"},emphasis:{focus:"adjacency",lineStyle:{opacity:1}},blur:{itemStyle:{opacity:.1},lineStyle:{opacity:.1}}}]};et.setOption(S,!0)}function ne(t){if(!p||!t||t.length===0)return;const e={tooltip:{trigger:"item",formatter:d=>d.name+": ¥"+$(d.value)+" ("+d.percent+"%)"},series:[{name:"消费漏斗",type:"funnel",left:"10%",top:60,bottom:60,width:"80%",min:0,max:t[0].value,minSize:"0%",maxSize:"100%",sort:"descending",gap:2,label:{show:!0,position:"inside",formatter:"{b}"},itemStyle:{borderColor:"#fff",borderWidth:1},data:t}]};p.setOption(e,!0)}function re(t){if(!s||!t.categories||t.categories.length===0)return;const e={tooltip:{trigger:"axis",axisPointer:{type:"cross",crossStyle:{color:"#999"}}},grid:{right:"10%",left:"5%",bottom:"10%"},legend:{data:["消费金额","累积占比"]},xAxis:[{type:"category",data:t.categories,axisPointer:{type:"shadow"},axisLabel:{interval:0,rotate:0}}],yAxis:[{type:"value",name:"金额"},{type:"value",name:"累积占比",min:0,max:100,interval:20,axisLabel:{formatter:"{value} %"}}],series:[{name:"消费金额",type:"bar",data:t.values,itemStyle:{color:d=>_t(d.name)}},{name:"累积占比",type:"line",yAxisIndex:1,data:t.percentages,itemStyle:{color:"#5470c6"},markLine:{data:[{yAxis:80,name:"80%线"}],lineStyle:{color:"#ee6666",type:"dashed"}}}]};s.setOption(e,!0)}function oe(t){if(!l||!t||t.length===0)return;const e={tooltip:{show:!0,formatter:d=>d.name+": ¥"+$(d.value)},series:[{type:"wordCloud",shape:"circle",left:"center",top:"center",width:"90%",height:"90%",sizeRange:[12,60],rotationRange:[0,0],rotationStep:0,gridSize:8,drawOutOfBound:!1,textStyle:{fontFamily:"sans-serif",fontWeight:"bold",color:()=>"rgb("+[Math.round(Math.random()*160),Math.round(Math.random()*160),Math.round(Math.random()*160)].join(",")+")"},emphasis:{focus:"self",textStyle:{shadowBlur:10,shadowColor:"#333"}},data:t}]};l.setOption(e,!0)}function le(t){if(!c||!t.data||t.data.length===0)return;const e=["",...t.categories],d=[[],...t.box_data],v=(w=>({boxWidth:"50%",scatterData:t.data.map(L=>{let dt=0;const Wt=(Math.random()-.5)*.6;return{value:[L.c+1+dt+Wt,L.v],merchant:L.m,date:L.d,categoryName:t.categories[L.c]}})}))(),S={tooltip:{trigger:"item",formatter:w=>{if(w.seriesType==="boxplot")return`${w.name}<br/>
                  最大值: ${$(w.data[5])}<br/>
                  Q3: ${$(w.data[4])}<br/>
                  中位数: ${$(w.data[3])}<br/>
                  Q1: ${$(w.data[2])}<br/>
                  最小值: ${$(w.data[1])}`;{const y=w.data;return`<strong>${y.categoryName}</strong><br/>
                  ${y.date}<br/>
                  ${y.merchant}<br/>
                  <strong>¥${$(y.value[1])}</strong>`}}},grid:{left:"10%",right:"10%",bottom:"15%"},xAxis:[{type:"category",data:e,boundaryGap:!0,axisLabel:{interval:0,rotate:0,formatter:w=>w.length>4?w.substring(0,4)+"..":w}},{type:"value",min:-.5,max:e.length-.5,show:!1}],yAxis:{type:"log",logBase:10,min:1,name:"金额 (元)",splitLine:{show:!0,lineStyle:{color:"#eee"}}},series:[{name:"summary",type:"boxplot",xAxisIndex:0,data:d,boxWidth:v.boxWidth,itemStyle:{color:"rgba(0, 0, 0, 0.02)",borderColor:"#666",borderWidth:1.5},symbolSize:0},{name:"transaction",type:"scatter",xAxisIndex:1,symbolSize:6,itemStyle:{color:w=>_t(w.data.categoryName),opacity:.6},data:v.scatterData}]};c.setOption(S,!0)}return fe(()=>i.currentFilter,()=>{b.value&&A(b.value)}),he(async()=>{try{n.setGlobalLoading(!0),await o.loadAvailableYears(),h.value=o.availableYears.sort((t,e)=>e-t),h.value.length>0&&(b.value=h.value[0],u.isDemo&&await new Promise(t=>setTimeout(t,500)),await A(b.value))}catch(t){console.error("Insights page init error:",t),n.showError("页面初始化失败: "+t.message)}finally{n.setGlobalLoading(!1)}}),ge(()=>{window.removeEventListener("resize",Z),st==null||st.dispose(),J==null||J.dispose(),K==null||K.dispose(),tt==null||tt.dispose(),V==null||V.dispose(),et==null||et.dispose(),p==null||p.dispose(),s==null||s.dispose(),l==null||l.dispose(),c==null||c.dispose(),f==null||f.dispose()}),(t,e)=>(ut(),ct("div",Ye,[a("div",qe,[e[9]||(e[9]=a("h1",{class:"page-title"},"消费洞察",-1)),a("div",Ne,[a("button",{onClick:M,class:"control-button",disabled:!g.value},[...e[7]||(e[7]=[a("i",{class:"fas fa-chevron-left"},null,-1)])],8,je),a("span",Ve,Lt(b.value)+"年",1),a("button",{onClick:C,class:"control-button",disabled:!k.value},[...e[8]||(e[8]=[a("i",{class:"fas fa-chevron-right"},null,-1)])],8,Xe)])]),Nt(n).globalLoading&&!r.value?(ut(),ct("div",Ze,[...e[10]||(e[10]=[a("div",{class:"loading-spinner"},null,-1),a("p",null,"加载中...",-1)])])):r.value?(ut(),ct("div",Ue,[a("div",Qe,[a("div",Je,[e[11]||(e[11]=a("div",{class:"card-header"},[a("h2",{class:"card-title"},"资金流向全景")],-1)),a("div",{class:"card-content",ref_key:"sankeyChartRef",ref:R},null,512)]),a("div",{class:"analysis-card story-entry-card",onClick:P},[...e[12]||(e[12]=[me('<div class="story-card-content" data-v-5690f728><div class="story-icon" data-v-5690f728><i class="fas fa-film" data-v-5690f728></i></div><div class="story-title" data-v-5690f728>年度消费故事</div><div class="story-desc" data-v-5690f728>点击开启您的时光之旅</div><div class="story-btn" data-v-5690f728>立即播放</div></div>',1)])])]),a("div",Ke,[a("div",ta,[e[13]||(e[13]=a("div",{class:"card-header"},[a("h2",{class:"card-title"},"消费画像")],-1)),a("div",{class:"card-content profile-content",ref_key:"profileContent",ref:pt},null,512)]),a("div",ea,[e[14]||(e[14]=a("div",{class:"card-header"},[a("h2",{class:"card-title"},"最常光顾")],-1)),a("div",aa,[a("div",{class:"merchant-list",ref_key:"merchantList",ref:xt},null,512)])]),a("div",ia,[e[15]||(e[15]=a("div",{class:"card-header"},[a("h2",{class:"card-title"},"消费场景")],-1)),a("div",sa,[a("div",na,[a("button",{class:Dt(["tab-btn",{active:T.value==="channel"}]),onClick:e[0]||(e[0]=d=>O("channel"))},"消费渠道",2),a("button",{class:Dt(["tab-btn",{active:T.value==="time"}]),onClick:e[1]||(e[1]=d=>O("time"))},"时段分布",2),a("button",{class:Dt(["tab-btn",{active:T.value==="amount"}]),onClick:e[2]||(e[2]=d=>O("amount"))},"金额层级",2),a("button",{class:Dt(["tab-btn",{active:T.value==="payment"}]),onClick:e[3]||(e[3]=d=>O("payment"))},"支付方式",2)]),a("div",{ref_key:"scenarioChartRef",ref:B,class:"chart-container"},null,512)])]),a("div",ra,[e[16]||(e[16]=a("div",{class:"card-header"},[a("h2",{class:"card-title"},"银行卡维度"),a("span",{class:"card-subtitle"},"按出资银行卡 / 钱包统计支出")],-1)),a("div",oa,[U.value.length?(ut(),ct("div",la,[(ut(!0),ct(pe,null,ye(U.value,(d,x)=>(ut(),ct("div",{key:x,class:"bankcard-row"},[a("span",{class:"bank-icon",style:Vt({background:d.color})},Lt(d.bank.slice(0,2)),5),a("div",da,[a("div",ca,Lt(d.label),1),a("div",ua,[a("div",{class:"bank-bar",style:Vt({width:W(d)+"%",background:d.color})},null,4)])]),a("div",va,[a("div",fa,"¥"+Lt(Nt($)(d.amount)),1),a("div",ha,Lt(d.count)+"笔",1)])]))),128))])):(ut(),ct("div",ga,"暂无银行卡数据"))])]),a("div",ma,[e[17]||(e[17]=a("div",{class:"card-header"},[a("h2",{class:"card-title"},"消费习惯")],-1)),a("div",pa,[a("div",{class:"habit-stats",ref_key:"habitStats",ref:St},null,512)])])]),a("div",ya,[a("div",wa,[e[18]||(e[18]=a("div",{class:"card-header"},[a("h2",{class:"card-title"},"拿铁因子")],-1)),a("div",{class:"card-content",ref_key:"latteContent",ref:yt},null,512)]),a("div",ba,[e[19]||(e[19]=a("div",{class:"card-header"},[a("h2",{class:"card-title"},"隐形订阅")],-1)),a("div",{class:"card-content",ref_key:"subContent",ref:ft},null,512)]),a("div",xa,[e[20]||(e[20]=a("div",{class:"card-header"},[a("h2",{class:"card-title"},"消费通胀")],-1)),a("div",{class:"card-content",ref_key:"inflationContent",ref:Ct},null,512)]),a("div",Sa,[e[21]||(e[21]=a("div",{class:"card-header"},[a("h2",{class:"card-title"},"品牌忠诚")],-1)),a("div",{class:"card-content",ref_key:"loyaltyContent",ref:wt},null,512)]),a("div",ka,[e[22]||(e[22]=a("div",{class:"card-header"},[a("h2",{class:"card-title"},"周末效应")],-1)),a("div",{class:"card-content",ref_key:"weekendContent",ref:$t},null,512)])]),a("div",_a,[e[32]||(e[32]=a("h2",{class:"section-title"},"深度洞察",-1)),e[33]||(e[33]=a("div",{class:"viz-section-header"},[a("div",{class:"section-subtitle"},[a("i",{class:"fas fa-clock"}),Bt(" 时间密码")])],-1)),a("div",Ma,[e[23]||(e[23]=a("div",{class:"card-header"},[a("h2",{class:"card-title"},"消费趋势河流")],-1)),a("div",{class:"card-content",ref_key:"themeRiverChartRef",ref:Q},null,512)]),a("div",Ca,[a("div",$a,[e[24]||(e[24]=a("div",{class:"card-header"},[a("h2",{class:"card-title"},"消费生物钟 (热力图)")],-1)),a("div",{class:"card-content",ref_key:"heatmapChartRef",ref:H},null,512)]),a("div",Ta,[e[25]||(e[25]=a("div",{class:"card-header"},[a("h2",{class:"card-title"},"季度消费结构")],-1)),a("div",{class:"card-content",ref_key:"radarChartRef",ref:j},null,512)])]),e[34]||(e[34]=a("div",{class:"viz-section-header"},[a("div",{class:"section-subtitle"},[a("i",{class:"fas fa-brain"}),Bt(" 决策心理")])],-1)),a("div",Fa,[e[26]||(e[26]=a("div",{class:"card-header"},[a("h2",{class:"card-title"},"消费象限 (频次 vs 均价)")],-1)),a("div",{class:"card-content",ref_key:"quadrantChartRef",ref:it},null,512)]),a("div",Ia,[a("div",Aa,[e[27]||(e[27]=a("div",{class:"card-header"},[a("h2",{class:"card-title"},"消费关联和弦")],-1)),a("div",{class:"card-content",ref_key:"chordChartRef",ref:bt},null,512)]),a("div",za,[e[28]||(e[28]=a("div",{class:"card-header"},[a("h2",{class:"card-title"},"消费金额漏斗")],-1)),a("div",{class:"card-content",ref_key:"funnelChartRef",ref:ot},null,512)])]),e[35]||(e[35]=a("div",{class:"viz-section-header"},[a("div",{class:"section-subtitle"},[a("i",{class:"fas fa-chart-pie"}),Bt(" 结构解析")])],-1)),a("div",La,[e[29]||(e[29]=a("div",{class:"card-header"},[a("h2",{class:"card-title"},"核心支出来源 (帕累托图)")],-1)),a("div",{class:"card-content",ref_key:"paretoChartRef",ref:gt,style:{height:"400px"}},null,512)]),a("div",Ea,[a("div",Ra,[e[30]||(e[30]=a("div",{class:"card-header"},[a("h2",{class:"card-title"},"消费热词云")],-1)),a("div",{class:"card-content",ref_key:"wordCloudChartRef",ref:mt},null,512)]),a("div",Da,[e[31]||(e[31]=a("div",{class:"card-header"},[a("h2",{class:"card-title"},"消费分布云图")],-1)),a("div",{class:"card-content",ref_key:"boxPlotChartRef",ref:vt},null,512)])])])])):(ut(),ct("div",Oa,[e[36]||(e[36]=a("i",{class:"fas fa-chart-bar empty-icon"},null,-1)),e[37]||(e[37]=a("p",null,"暂无数据",-1)),a("button",{class:"btn btn-primary",onClick:e[4]||(e[4]=d=>t.$router.push("/settings"))}," 上传账单 ")])),Y.value?(ut(),ct("div",{key:3,class:"story-modal",onClick:e[6]||(e[6]=we(d=>Y.value=!1,["self"])),style:{display:"flex"}},[a("div",Pa,[a("button",{class:"close-story",onClick:e[5]||(e[5]=d=>Y.value=!1)},[...e[38]||(e[38]=[a("i",{class:"fas fa-times"},null,-1)])]),a("div",{class:"story-slides",ref_key:"storySlides",ref:Tt},null,512),a("div",Wa,[a("button",{class:"story-btn prev",onClick:F},[...e[39]||(e[39]=[a("i",{class:"fas fa-chevron-left"},null,-1)])]),a("div",{class:"story-indicators",ref_key:"storyIndicators",ref:Ft},null,512),a("button",{class:"story-btn next",onClick:I},[...e[40]||(e[40]=[a("i",{class:"fas fa-chevron-right"},null,-1)])])])])])):be("",!0)]))}},Na=de(Ba,[["__scopeId","data-v-5690f728"]]);export{Na as default};
