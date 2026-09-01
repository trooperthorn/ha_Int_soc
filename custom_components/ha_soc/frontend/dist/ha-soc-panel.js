function t(t,e,s,i){var a,r=arguments.length,o=r<3?e:null===i?i=Object.getOwnPropertyDescriptor(e,s):i;if("object"==typeof Reflect&&"function"==typeof Reflect.decorate)o=Reflect.decorate(t,e,s,i);else for(var n=t.length-1;n>=0;n--)(a=t[n])&&(o=(r<3?a(o):r>3?a(e,s,o):a(e,s))||o);return r>3&&o&&Object.defineProperty(e,s,o),o}"function"==typeof SuppressedError&&SuppressedError;
/**
 * @license
 * Copyright 2019 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const e=globalThis,s=e.ShadowRoot&&(void 0===e.ShadyCSS||e.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,i=Symbol(),a=new WeakMap;let r=class{constructor(t,e,s){if(this._$cssResult$=!0,s!==i)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=t,this.t=e}get styleSheet(){let t=this.o;const e=this.t;if(s&&void 0===t){const s=void 0!==e&&1===e.length;s&&(t=a.get(e)),void 0===t&&((this.o=t=new CSSStyleSheet).replaceSync(this.cssText),s&&a.set(e,t))}return t}toString(){return this.cssText}};const o=(t,...e)=>{const s=1===t.length?t[0]:e.reduce((e,s,i)=>e+(t=>{if(!0===t._$cssResult$)return t.cssText;if("number"==typeof t)return t;throw Error("Value passed to 'css' function must be a 'css' function result: "+t+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(s)+t[i+1],t[0]);return new r(s,t,i)},n=s?t=>t:t=>t instanceof CSSStyleSheet?(t=>{let e="";for(const s of t.cssRules)e+=s.cssText;return(t=>new r("string"==typeof t?t:t+"",void 0,i))(e)})(t):t,{is:l,defineProperty:d,getOwnPropertyDescriptor:c,getOwnPropertyNames:p,getOwnPropertySymbols:h,getPrototypeOf:u}=Object,g=globalThis,_=g.trustedTypes,v=_?_.emptyScript:"",m=g.reactiveElementPolyfillSupport,y=(t,e)=>t,b={toAttribute(t,e){switch(e){case Boolean:t=t?v:null;break;case Object:case Array:t=null==t?t:JSON.stringify(t)}return t},fromAttribute(t,e){let s=t;switch(e){case Boolean:s=null!==t;break;case Number:s=null===t?null:Number(t);break;case Object:case Array:try{s=JSON.parse(t)}catch(t){s=null}}return s}},f=(t,e)=>!l(t,e),$={attribute:!0,type:String,converter:b,reflect:!1,useDefault:!1,hasChanged:f};
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */Symbol.metadata??=Symbol("metadata"),g.litPropertyMetadata??=new WeakMap;let w=class extends HTMLElement{static addInitializer(t){this._$Ei(),(this.l??=[]).push(t)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(t,e=$){if(e.state&&(e.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(t)&&((e=Object.create(e)).wrapped=!0),this.elementProperties.set(t,e),!e.noAccessor){const s=Symbol(),i=this.getPropertyDescriptor(t,s,e);void 0!==i&&d(this.prototype,t,i)}}static getPropertyDescriptor(t,e,s){const{get:i,set:a}=c(this.prototype,t)??{get(){return this[e]},set(t){this[e]=t}};return{get:i,set(e){const r=i?.call(this);a?.call(this,e),this.requestUpdate(t,r,s)},configurable:!0,enumerable:!0}}static getPropertyOptions(t){return this.elementProperties.get(t)??$}static _$Ei(){if(this.hasOwnProperty(y("elementProperties")))return;const t=u(this);t.finalize(),void 0!==t.l&&(this.l=[...t.l]),this.elementProperties=new Map(t.elementProperties)}static finalize(){if(this.hasOwnProperty(y("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(y("properties"))){const t=this.properties,e=[...p(t),...h(t)];for(const s of e)this.createProperty(s,t[s])}const t=this[Symbol.metadata];if(null!==t){const e=litPropertyMetadata.get(t);if(void 0!==e)for(const[t,s]of e)this.elementProperties.set(t,s)}this._$Eh=new Map;for(const[t,e]of this.elementProperties){const s=this._$Eu(t,e);void 0!==s&&this._$Eh.set(s,t)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(t){const e=[];if(Array.isArray(t)){const s=new Set(t.flat(1/0).reverse());for(const t of s)e.unshift(n(t))}else void 0!==t&&e.push(n(t));return e}static _$Eu(t,e){const s=e.attribute;return!1===s?void 0:"string"==typeof s?s:"string"==typeof t?t.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(t=>this.enableUpdating=t),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(t=>t(this))}addController(t){(this._$EO??=new Set).add(t),void 0!==this.renderRoot&&this.isConnected&&t.hostConnected?.()}removeController(t){this._$EO?.delete(t)}_$E_(){const t=new Map,e=this.constructor.elementProperties;for(const s of e.keys())this.hasOwnProperty(s)&&(t.set(s,this[s]),delete this[s]);t.size>0&&(this._$Ep=t)}createRenderRoot(){const t=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return((t,i)=>{if(s)t.adoptedStyleSheets=i.map(t=>t instanceof CSSStyleSheet?t:t.styleSheet);else for(const s of i){const i=document.createElement("style"),a=e.litNonce;void 0!==a&&i.setAttribute("nonce",a),i.textContent=s.cssText,t.appendChild(i)}})(t,this.constructor.elementStyles),t}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(t=>t.hostConnected?.())}enableUpdating(t){}disconnectedCallback(){this._$EO?.forEach(t=>t.hostDisconnected?.())}attributeChangedCallback(t,e,s){this._$AK(t,s)}_$ET(t,e){const s=this.constructor.elementProperties.get(t),i=this.constructor._$Eu(t,s);if(void 0!==i&&!0===s.reflect){const a=(void 0!==s.converter?.toAttribute?s.converter:b).toAttribute(e,s.type);this._$Em=t,null==a?this.removeAttribute(i):this.setAttribute(i,a),this._$Em=null}}_$AK(t,e){const s=this.constructor,i=s._$Eh.get(t);if(void 0!==i&&this._$Em!==i){const t=s.getPropertyOptions(i),a="function"==typeof t.converter?{fromAttribute:t.converter}:void 0!==t.converter?.fromAttribute?t.converter:b;this._$Em=i;const r=a.fromAttribute(e,t.type);this[i]=r??this._$Ej?.get(i)??r,this._$Em=null}}requestUpdate(t,e,s,i=!1,a){if(void 0!==t){const r=this.constructor;if(!1===i&&(a=this[t]),s??=r.getPropertyOptions(t),!((s.hasChanged??f)(a,e)||s.useDefault&&s.reflect&&a===this._$Ej?.get(t)&&!this.hasAttribute(r._$Eu(t,s))))return;this.C(t,e,s)}!1===this.isUpdatePending&&(this._$ES=this._$EP())}C(t,e,{useDefault:s,reflect:i,wrapped:a},r){s&&!(this._$Ej??=new Map).has(t)&&(this._$Ej.set(t,r??e??this[t]),!0!==a||void 0!==r)||(this._$AL.has(t)||(this.hasUpdated||s||(e=void 0),this._$AL.set(t,e)),!0===i&&this._$Em!==t&&(this._$Eq??=new Set).add(t))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(t){Promise.reject(t)}const t=this.scheduleUpdate();return null!=t&&await t,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(const[t,e]of this._$Ep)this[t]=e;this._$Ep=void 0}const t=this.constructor.elementProperties;if(t.size>0)for(const[e,s]of t){const{wrapped:t}=s,i=this[e];!0!==t||this._$AL.has(e)||void 0===i||this.C(e,void 0,s,i)}}let t=!1;const e=this._$AL;try{t=this.shouldUpdate(e),t?(this.willUpdate(e),this._$EO?.forEach(t=>t.hostUpdate?.()),this.update(e)):this._$EM()}catch(e){throw t=!1,this._$EM(),e}t&&this._$AE(e)}willUpdate(t){}_$AE(t){this._$EO?.forEach(t=>t.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(t)),this.updated(t)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(t){return!0}update(t){this._$Eq&&=this._$Eq.forEach(t=>this._$ET(t,this[t])),this._$EM()}updated(t){}firstUpdated(t){}};w.elementStyles=[],w.shadowRootOptions={mode:"open"},w[y("elementProperties")]=new Map,w[y("finalized")]=new Map,m?.({ReactiveElement:w}),(g.reactiveElementVersions??=[]).push("2.1.2");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const x=globalThis,k=t=>t,S=x.trustedTypes,C=S?S.createPolicy("lit-html",{createHTML:t=>t}):void 0,A="$lit$",P=`lit$${Math.random().toFixed(9).slice(2)}$`,z="?"+P,E=`<${z}>`,R=document,I=()=>R.createComment(""),F=t=>null===t||"object"!=typeof t&&"function"!=typeof t,T=Array.isArray,N="[ \t\n\f\r]",L=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,O=/-->/g,D=/>/g,U=RegExp(`>|${N}(?:([^\\s"'>=/]+)(${N}*=${N}*(?:[^ \t\n\f\r"'\`<>=]|("|')|))|$)`,"g"),M=/'/g,H=/"/g,V=/^(?:script|style|textarea|title)$/i,B=(t=>(e,...s)=>({_$litType$:t,strings:e,values:s}))(1),j=Symbol.for("lit-noChange"),W=Symbol.for("lit-nothing"),q=new WeakMap,K=R.createTreeWalker(R,129);function G(t,e){if(!T(t)||!t.hasOwnProperty("raw"))throw Error("invalid template strings array");return void 0!==C?C.createHTML(e):e}const Z=(t,e)=>{const s=t.length-1,i=[];let a,r=2===e?"<svg>":3===e?"<math>":"",o=L;for(let e=0;e<s;e++){const s=t[e];let n,l,d=-1,c=0;for(;c<s.length&&(o.lastIndex=c,l=o.exec(s),null!==l);)c=o.lastIndex,o===L?"!--"===l[1]?o=O:void 0!==l[1]?o=D:void 0!==l[2]?(V.test(l[2])&&(a=RegExp("</"+l[2],"g")),o=U):void 0!==l[3]&&(o=U):o===U?">"===l[0]?(o=a??L,d=-1):void 0===l[1]?d=-2:(d=o.lastIndex-l[2].length,n=l[1],o=void 0===l[3]?U:'"'===l[3]?H:M):o===H||o===M?o=U:o===O||o===D?o=L:(o=U,a=void 0);const p=o===U&&t[e+1].startsWith("/>")?" ":"";r+=o===L?s+E:d>=0?(i.push(n),s.slice(0,d)+A+s.slice(d)+P+p):s+P+(-2===d?e:p)}return[G(t,r+(t[s]||"<?>")+(2===e?"</svg>":3===e?"</math>":"")),i]};class J{constructor({strings:t,_$litType$:e},s){let i;this.parts=[];let a=0,r=0;const o=t.length-1,n=this.parts,[l,d]=Z(t,e);if(this.el=J.createElement(l,s),K.currentNode=this.el.content,2===e||3===e){const t=this.el.content.firstChild;t.replaceWith(...t.childNodes)}for(;null!==(i=K.nextNode())&&n.length<o;){if(1===i.nodeType){if(i.hasAttributes())for(const t of i.getAttributeNames())if(t.endsWith(A)){const e=d[r++],s=i.getAttribute(t).split(P),o=/([.?@])?(.*)/.exec(e);n.push({type:1,index:a,name:o[2],strings:s,ctor:"."===o[1]?et:"?"===o[1]?st:"@"===o[1]?it:tt}),i.removeAttribute(t)}else t.startsWith(P)&&(n.push({type:6,index:a}),i.removeAttribute(t));if(V.test(i.tagName)){const t=i.textContent.split(P),e=t.length-1;if(e>0){i.textContent=S?S.emptyScript:"";for(let s=0;s<e;s++)i.append(t[s],I()),K.nextNode(),n.push({type:2,index:++a});i.append(t[e],I())}}}else if(8===i.nodeType)if(i.data===z)n.push({type:2,index:a});else{let t=-1;for(;-1!==(t=i.data.indexOf(P,t+1));)n.push({type:7,index:a}),t+=P.length-1}a++}}static createElement(t,e){const s=R.createElement("template");return s.innerHTML=t,s}}function Y(t,e,s=t,i){if(e===j)return e;let a=void 0!==i?s._$Co?.[i]:s._$Cl;const r=F(e)?void 0:e._$litDirective$;return a?.constructor!==r&&(a?._$AO?.(!1),void 0===r?a=void 0:(a=new r(t),a._$AT(t,s,i)),void 0!==i?(s._$Co??=[])[i]=a:s._$Cl=a),void 0!==a&&(e=Y(t,a._$AS(t,e.values),a,i)),e}class Q{constructor(t,e){this._$AV=[],this._$AN=void 0,this._$AD=t,this._$AM=e}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(t){const{el:{content:e},parts:s}=this._$AD,i=(t?.creationScope??R).importNode(e,!0);K.currentNode=i;let a=K.nextNode(),r=0,o=0,n=s[0];for(;void 0!==n;){if(r===n.index){let e;2===n.type?e=new X(a,a.nextSibling,this,t):1===n.type?e=new n.ctor(a,n.name,n.strings,this,t):6===n.type&&(e=new at(a,this,t)),this._$AV.push(e),n=s[++o]}r!==n?.index&&(a=K.nextNode(),r++)}return K.currentNode=R,i}p(t){let e=0;for(const s of this._$AV)void 0!==s&&(void 0!==s.strings?(s._$AI(t,s,e),e+=s.strings.length-2):s._$AI(t[e])),e++}}class X{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(t,e,s,i){this.type=2,this._$AH=W,this._$AN=void 0,this._$AA=t,this._$AB=e,this._$AM=s,this.options=i,this._$Cv=i?.isConnected??!0}get parentNode(){let t=this._$AA.parentNode;const e=this._$AM;return void 0!==e&&11===t?.nodeType&&(t=e.parentNode),t}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(t,e=this){t=Y(this,t,e),F(t)?t===W||null==t||""===t?(this._$AH!==W&&this._$AR(),this._$AH=W):t!==this._$AH&&t!==j&&this._(t):void 0!==t._$litType$?this.$(t):void 0!==t.nodeType?this.T(t):(t=>T(t)||"function"==typeof t?.[Symbol.iterator])(t)?this.k(t):this._(t)}O(t){return this._$AA.parentNode.insertBefore(t,this._$AB)}T(t){this._$AH!==t&&(this._$AR(),this._$AH=this.O(t))}_(t){this._$AH!==W&&F(this._$AH)?this._$AA.nextSibling.data=t:this.T(R.createTextNode(t)),this._$AH=t}$(t){const{values:e,_$litType$:s}=t,i="number"==typeof s?this._$AC(t):(void 0===s.el&&(s.el=J.createElement(G(s.h,s.h[0]),this.options)),s);if(this._$AH?._$AD===i)this._$AH.p(e);else{const t=new Q(i,this),s=t.u(this.options);t.p(e),this.T(s),this._$AH=t}}_$AC(t){let e=q.get(t.strings);return void 0===e&&q.set(t.strings,e=new J(t)),e}k(t){T(this._$AH)||(this._$AH=[],this._$AR());const e=this._$AH;let s,i=0;for(const a of t)i===e.length?e.push(s=new X(this.O(I()),this.O(I()),this,this.options)):s=e[i],s._$AI(a),i++;i<e.length&&(this._$AR(s&&s._$AB.nextSibling,i),e.length=i)}_$AR(t=this._$AA.nextSibling,e){for(this._$AP?.(!1,!0,e);t!==this._$AB;){const e=k(t).nextSibling;k(t).remove(),t=e}}setConnected(t){void 0===this._$AM&&(this._$Cv=t,this._$AP?.(t))}}class tt{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(t,e,s,i,a){this.type=1,this._$AH=W,this._$AN=void 0,this.element=t,this.name=e,this._$AM=i,this.options=a,s.length>2||""!==s[0]||""!==s[1]?(this._$AH=Array(s.length-1).fill(new String),this.strings=s):this._$AH=W}_$AI(t,e=this,s,i){const a=this.strings;let r=!1;if(void 0===a)t=Y(this,t,e,0),r=!F(t)||t!==this._$AH&&t!==j,r&&(this._$AH=t);else{const i=t;let o,n;for(t=a[0],o=0;o<a.length-1;o++)n=Y(this,i[s+o],e,o),n===j&&(n=this._$AH[o]),r||=!F(n)||n!==this._$AH[o],n===W?t=W:t!==W&&(t+=(n??"")+a[o+1]),this._$AH[o]=n}r&&!i&&this.j(t)}j(t){t===W?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,t??"")}}class et extends tt{constructor(){super(...arguments),this.type=3}j(t){this.element[this.name]=t===W?void 0:t}}class st extends tt{constructor(){super(...arguments),this.type=4}j(t){this.element.toggleAttribute(this.name,!!t&&t!==W)}}class it extends tt{constructor(t,e,s,i,a){super(t,e,s,i,a),this.type=5}_$AI(t,e=this){if((t=Y(this,t,e,0)??W)===j)return;const s=this._$AH,i=t===W&&s!==W||t.capture!==s.capture||t.once!==s.once||t.passive!==s.passive,a=t!==W&&(s===W||i);i&&this.element.removeEventListener(this.name,this,s),a&&this.element.addEventListener(this.name,this,t),this._$AH=t}handleEvent(t){"function"==typeof this._$AH?this._$AH.call(this.options?.host??this.element,t):this._$AH.handleEvent(t)}}class at{constructor(t,e,s){this.element=t,this.type=6,this._$AN=void 0,this._$AM=e,this.options=s}get _$AU(){return this._$AM._$AU}_$AI(t){Y(this,t)}}const rt=x.litHtmlPolyfillSupport;rt?.(J,X),(x.litHtmlVersions??=[]).push("3.3.3");const ot=globalThis;
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */class nt extends w{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){const t=super.createRenderRoot();return this.renderOptions.renderBefore??=t.firstChild,t}update(t){const e=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(t),this._$Do=((t,e,s)=>{const i=s?.renderBefore??e;let a=i._$litPart$;if(void 0===a){const t=s?.renderBefore??null;i._$litPart$=a=new X(e.insertBefore(I(),t),t,void 0,s??{})}return a._$AI(t),a})(e,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return j}}nt._$litElement$=!0,nt.finalized=!0,ot.litElementHydrateSupport?.({LitElement:nt});const lt=ot.litElementPolyfillSupport;lt?.({LitElement:nt}),(ot.litElementVersions??=[]).push("4.2.2");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const dt=t=>(e,s)=>{void 0!==s?s.addInitializer(()=>{customElements.define(t,e)}):customElements.define(t,e)},ct={attribute:!0,type:String,converter:b,reflect:!1,hasChanged:f},pt=(t=ct,e,s)=>{const{kind:i,metadata:a}=s;let r=globalThis.litPropertyMetadata.get(a);if(void 0===r&&globalThis.litPropertyMetadata.set(a,r=new Map),"setter"===i&&((t=Object.create(t)).wrapped=!0),r.set(s.name,t),"accessor"===i){const{name:i}=s;return{set(s){const a=e.get.call(this);e.set.call(this,s),this.requestUpdate(i,a,t,!0,s)},init(e){return void 0!==e&&this.C(i,void 0,t,e),e}}}if("setter"===i){const{name:i}=s;return function(s){const a=this[i];e.call(this,s),this.requestUpdate(i,a,t,!0,s)}}throw Error("Unsupported decorator location: "+i)};
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */function ht(t){return(e,s)=>"object"==typeof s?pt(t,e,s):((t,e,s)=>{const i=e.hasOwnProperty(s);return e.constructor.createProperty(s,t),i?Object.getOwnPropertyDescriptor(e,s):void 0})(t,e,s)}
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */function ut(t){return ht({...t,state:!0,attribute:!1})}const gt=(t,e)=>t.callWS(e),_t=t=>gt(t,{type:"ha_soc/users/list"}).then(t=>t.users),vt=t=>gt(t,{type:"ha_soc/risk/list"}).then(t=>t.risk),mt=(t,e)=>gt(t,{type:"ha_soc/detections/list",status:e}).then(t=>t.detections),yt=(t,e,s)=>gt(t,{type:"ha_soc/detections/set_status",detection_id:e,status:s}),bt=t=>gt(t,{type:"ha_soc/detections/thresholds"}).then(t=>t.rules),ft=t=>gt(t,{type:"ha_soc/vulns/list"}).then(t=>t.findings),$t=t=>gt(t,{type:"ha_soc/logs/fault"}),wt=t=>gt(t,{type:"ha_soc/logs/targets"}),xt=t=>gt(t,{type:"ha_soc/health/list"}),kt=t=>gt(t,{type:"ha_soc/dashboard/devices"}),St=t=>gt(t,{type:"ha_soc/dashboard/integrations"}),Ct=t=>gt(t,{type:"ha_soc/access/info"}),At=t=>gt(t,{type:"ha_soc/probe/status"}),Pt=t=>gt(t,{type:"ha_soc/firewall/status"}),zt=t=>gt(t,{type:"ha_soc/peripherals/list"}),Et=t=>gt(t,{type:"ha_soc/entity_remap/broken_references"}).then(t=>t.broken),Rt=t=>gt(t,{type:"ha_soc/security_health/list"}),It=(t,e)=>gt(t,{type:"ha_soc/settings/set",...e}),Ft=o`
  :host {
    display: block;
    padding: 20px clamp(14px, 2vw, 24px) 28px;
    max-width: 1400px;
    margin: 0 auto;

    /* Validated categorical palette (dataviz skill reference instance) —
       adjacent-pair CVD/contrast checked for chart use (bars, lines,
       stacks). Light values here; .dark overrides the dark-mode steps. */
    --cat-1: #2a78d6;
    --cat-2: #eb6834;
    --cat-3: #1baf7a;
    --cat-4: #eda100;
    --cat-5: #e87ba4;
    --cat-6: #008300;
    --cat-7: #4a3aa7;
    --cat-8: #e34948;
    --cat-other: #9aa0a6;

    /* Reserved status roles — never reused as a plain series color. */
    --status-good: #0ca30c;
    --status-warning: #fab219;
    --status-serious: #ec835a;
    --status-critical: #d03b3b;
  }
  :host(.dark) {
    --cat-1: #3987e5;
    --cat-2: #d95926;
    --cat-3: #199e70;
    --cat-4: #c98500;
    --cat-5: #d55181;
    --cat-6: #008300;
    --cat-7: #9085e9;
    --cat-8: #e66767;
    --cat-other: #7a807f;
  }
  .tabs {
    display: flex;
    gap: 4px;
    border-bottom: 1px solid var(--divider-color);
    margin-bottom: 16px;
    overflow-x: auto;
  }
  .tab {
    padding: 12px 16px;
    cursor: pointer;
    font-size: 14px;
    font-weight: 500;
    color: var(--secondary-text-color);
    border-bottom: 2px solid transparent;
    white-space: nowrap;
  }
  .tab.active {
    color: var(--primary-color);
    border-bottom-color: var(--primary-color);
  }
  .card {
    background: var(--card-background-color, #fff);
    border-radius: var(--ha-card-border-radius, 12px);
    border: 1px solid var(--divider-color);
    box-shadow: none;
    padding: 16px;
    margin-bottom: 16px;
  }
  .card h3 {
    margin: 0 0 12px;
    font-size: 15px;
    font-weight: 650;
    letter-spacing: -0.005em;
    color: var(--primary-text-color);
  }
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
  }
  th,
  td {
    text-align: left;
    padding: 8px 10px;
    border-bottom: 1px solid var(--divider-color);
    vertical-align: top;
  }
  th {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    color: var(--secondary-text-color);
  }
  tr:hover td {
    background: rgba(var(--rgb-primary-text-color, 0, 0, 0), 0.03);
  }
  tr.row-disabled td {
    background: rgba(var(--rgb-error-color, 219, 68, 55), 0.05);
    color: var(--secondary-text-color);
  }
  tr.row-disabled td:first-child > div:first-child {
    text-decoration: line-through;
    text-decoration-color: var(--secondary-text-color);
  }
  .pill {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    font-size: 11px;
    font-weight: 600;
    padding: 3px 8px;
    border-radius: 100px;
    background: rgba(var(--rgb-primary-text-color, 0, 0, 0), 0.06);
  }
  .pill .dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
  }
  .pill.critical .dot,
  .pill.high .dot {
    background: var(--error-color, #db4437);
  }
  .pill.medium .dot {
    background: var(--warning-color, #ffa600);
  }
  .pill.low .dot,
  .pill.info .dot {
    background: var(--disabled-text-color, #888);
  }
  .pill.good .dot {
    background: var(--success-color, #43a047);
  }
  .tag {
    font-size: 10.5px;
    padding: 2px 6px;
    border-radius: 5px;
    font-family: var(--code-font-family, monospace);
  }
  .tag.enforced {
    background: rgba(67, 160, 71, 0.15);
    color: var(--success-color, #43a047);
  }
  .tag.cosmetic {
    background: rgba(255, 166, 0, 0.18);
    color: var(--warning-color, #ffa600);
  }
  button.ha-btn {
    font: inherit;
    font-weight: 500;
    font-size: 13px;
    color: var(--primary-color);
    background: none;
    border: 1px solid var(--primary-color);
    border-radius: 8px;
    padding: 6px 12px;
    cursor: pointer;
  }
  button.ha-btn:hover {
    background: rgba(var(--rgb-primary-color, 3, 155, 229), 0.08);
  }
  button.ha-btn.danger {
    color: var(--error-color, #db4437);
    border-color: var(--error-color, #db4437);
  }
  button.ha-btn:disabled {
    opacity: 0.5;
    cursor: default;
  }
  input,
  select {
    font: inherit;
    font-size: 13px;
    padding: 6px 8px;
    border-radius: 6px;
    border: 1px solid var(--divider-color);
    background: var(--card-background-color, #fff);
    color: var(--primary-text-color);
  }
  .muted {
    color: var(--secondary-text-color);
  }
  .toolbar {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 12px;
    flex-wrap: wrap;
  }
  .toolbar .spacer {
    flex: 1;
  }
  .empty {
    color: var(--secondary-text-color);
    font-size: 13px;
    padding: 24px 0;
    text-align: center;
  }
  .chips {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
  }
  .chip {
    font-size: 10.5px;
    background: rgba(var(--rgb-primary-text-color, 0, 0, 0), 0.06);
    padding: 2px 6px;
    border-radius: 5px;
  }
  .settings-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    padding: 10px 0;
    border-bottom: 1px solid var(--divider-color);
    font-size: 13.5px;
  }
  .settings-row:last-child {
    border-bottom: none;
  }
  .settings-row > span:first-child {
    color: var(--primary-text-color);
    flex: 1;
  }
  .settings-row input[type="number"],
  .settings-row input[type="password"],
  .settings-row input[type="text"] {
    width: 160px;
    text-align: right;
  }
  .settings-row select {
    min-width: 220px;
  }
  .fw-subhead {
    margin: 16px 0 6px;
    font-size: 12.5px;
    color: var(--secondary-text-color);
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }
  /* Accessible sortable column headers (see sortable.ts): the whole header
     is a real button (keyboard focus + Enter/Space), aria-sort on the th
     conveys state to assistive tech, the arrow is decorative only. */
  th.sortable {
    padding: 0;
  }
  th.sortable .sort-btn {
    font: inherit;
    font-size: 11px;
    font-weight: inherit;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    color: var(--secondary-text-color);
    background: none;
    border: none;
    padding: 8px 10px;
    width: 100%;
    text-align: left;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 4px;
    white-space: nowrap;
  }
  th.sortable.num .sort-btn {
    justify-content: flex-end;
    text-align: right;
  }
  th.sortable .sort-btn:hover,
  th.sortable .sort-btn:focus-visible {
    color: var(--primary-color);
  }
  th.sortable .sort-arrow {
    opacity: 0.35;
    font-size: 10px;
  }
  th.sortable .sort-arrow.active {
    opacity: 1;
    color: var(--primary-color);
  }
`,Tt={order:[],hidden:[]};function Nt(t,e){const s=new Map(t.map(t=>[t.id,t])),i=new Set,a=[];for(const t of e.order){const e=s.get(t);e&&!i.has(t)&&(a.push(e),i.add(t))}for(const e of t)i.has(e.id)||(a.push(e),i.add(e.id));return a}let Lt=class extends nt{constructor(){super(...arguments),this.sections=[],this.layout=Tt,this.editMode=!1,this._dragId=null}render(){const t=Nt(this.sections,this.layout),e=new Set(this.layout.hidden);return this.editMode?B`
      <div class="customize-list">
        <p class="customize-hint">
          Drag the handle, or use ▲/▼, to reorder. Hide a section to remove it from this
          page without losing its data — you can bring it back here anytime.
        </p>
        ${t.map((s,i)=>this._renderEditRow(s,i,t.length,e.has(s.id)))}
      </div>
    `:B`${t.filter(t=>!e.has(t.id)).map(t=>t.render())}`}_renderEditRow(t,e,s,i){return B`
      <div
        class="customize-row ${i?"row-hidden":""} ${this._dragId===t.id?"dragging":""}"
        draggable="true"
        @dragstart=${e=>this._onDragStart(e,t.id)}
        @dragover=${t=>t.preventDefault()}
        @drop=${e=>this._onDrop(e,t.id)}
        @dragend=${()=>this._onDragEnd()}
      >
        <span class="handle" aria-hidden="true" title="Drag to reorder">⠿⠿</span>
        <span class="row-title">${t.title}</span>
        <button
          type="button"
          class="icon-btn"
          title="Move up"
          ?disabled=${0===e}
          @click=${()=>this._move(t.id,-1)}
        >
          ▲
        </button>
        <button
          type="button"
          class="icon-btn"
          title="Move down"
          ?disabled=${e===s-1}
          @click=${()=>this._move(t.id,1)}
        >
          ▼
        </button>
        ${!1===t.hideable?W:B`
              <button
                type="button"
                class="icon-btn ${i?"":"visibility-on"}"
                title=${i?"Show this section":"Hide this section"}
                @click=${()=>this._toggleHidden(t.id)}
              >
                ${i?"Show":"Hide"}
              </button>
            `}
      </div>
    `}_move(t,e){const s=Nt(this.sections,this.layout).map(t=>t.id),i=s.indexOf(t),a=i+e;i<0||a<0||a>=s.length||([s[i],s[a]]=[s[a],s[i]],this._emitChange(s,this.layout.hidden))}_toggleHidden(t){const e=this.layout.hidden.includes(t)?this.layout.hidden.filter(e=>e!==t):[...this.layout.hidden,t],s=Nt(this.sections,this.layout).map(t=>t.id);this._emitChange(s,e)}_onDragStart(t,e){this._dragId=e,t.dataTransfer?.setData("text/plain",e),t.dataTransfer&&(t.dataTransfer.effectAllowed="move"),this.requestUpdate()}_onDrop(t,e){t.preventDefault();const s=this._dragId;if(!s||s===e)return;const i=Nt(this.sections,this.layout).map(t=>t.id),a=i.indexOf(s),r=i.indexOf(e);a<0||r<0||(i.splice(a,1),i.splice(r,0,s),this._emitChange(i,this.layout.hidden))}_onDragEnd(){this._dragId=null,this.requestUpdate()}_emitChange(t,e){this.dispatchEvent(new CustomEvent("layout-change",{detail:{order:t,hidden:e},bubbles:!0,composed:!0}))}};Lt.styles=o`
    :host {
      display: block;
    }
    .customize-list {
      display: flex;
      flex-direction: column;
      gap: 6px;
      margin-bottom: 16px;
      padding: 10px;
      border-radius: var(--ha-card-border-radius, 12px);
      background: rgba(var(--rgb-primary-color, 3, 155, 229), 0.06);
      border: 1px dashed rgba(var(--rgb-primary-color, 3, 155, 229), 0.35);
    }
    .customize-hint {
      font-size: 12px;
      color: var(--secondary-text-color);
      margin: 0 0 4px 2px;
    }
    .customize-row {
      display: flex;
      align-items: center;
      gap: 8px;
      background: var(--card-background-color, #fff);
      border-radius: 8px;
      padding: 8px 10px;
      box-shadow: 0 1px 2px rgba(0, 0, 0, 0.08);
    }
    .customize-row.dragging {
      opacity: 0.4;
    }
    .customize-row.row-hidden {
      opacity: 0.55;
    }
    .handle {
      cursor: grab;
      color: var(--secondary-text-color);
      font-size: 16px;
      line-height: 1;
      user-select: none;
    }
    .row-title {
      flex: 1;
      font-size: 13.5px;
      font-weight: 600;
    }
    .row-hidden .row-title {
      text-decoration: line-through;
      color: var(--secondary-text-color);
    }
    .icon-btn {
      background: none;
      border: 1px solid var(--divider-color);
      border-radius: 6px;
      cursor: pointer;
      font-size: 12px;
      padding: 3px 8px;
      color: var(--primary-text-color);
    }
    .icon-btn:hover {
      background: rgba(var(--rgb-primary-text-color, 0, 0, 0), 0.05);
    }
    .icon-btn:disabled {
      opacity: 0.3;
      cursor: default;
    }
    .icon-btn.visibility-on {
      color: var(--primary-color);
      border-color: var(--primary-color);
    }
  `,t([ht({attribute:!1})],Lt.prototype,"sections",void 0),t([ht({attribute:!1})],Lt.prototype,"layout",void 0),t([ht({type:Boolean})],Lt.prototype,"editMode",void 0),Lt=t([dt("ha-soc-customize-list")],Lt);class Ot extends nt{constructor(){super(...arguments),this.customizeMode=!1,this._layout=Tt,this._onLayoutChange=t=>{var e,s,i;this._layout=t.detail,(e=this.hass,s=this.viewId,i=t.detail,gt(e,{type:"ha_soc/layout/set",view_id:s,order:i.order,hidden:i.hidden})).catch(()=>{})}}connectedCallback(){super.connectedCallback(),this._loadLayout()}async _loadLayout(){try{this._layout=await(t=this.hass,e=this.viewId,gt(t,{type:"ha_soc/layout/get",view_id:e}))}catch{this._layout=Tt}var t,e}_renderSections(t){return B`
      <ha-soc-customize-list
        .sections=${t}
        .layout=${this._layout}
        .editMode=${this.customizeMode}
        @layout-change=${this._onLayoutChange}
      ></ha-soc-customize-list>
    `}}function Dt(t,e,s){if(!e)return t;const i=s[e.key];return i?t.map((t,e)=>({row:t,i:e})).sort((t,s)=>{const a=i(t.row),r=i(s.row),o=null==a||""===a,n=null==r||""===r;if(o&&n)return t.i-s.i;if(o)return 1;if(n)return-1;let l;return l="number"==typeof a&&"number"==typeof r?a-r:"boolean"==typeof a&&"boolean"==typeof r?Number(a)-Number(r):String(a).localeCompare(String(r),void 0,{sensitivity:"base",numeric:!0}),0!==l?l*e.dir:t.i-s.i}).map(t=>t.row):t}function Ut(t,e,s,i,a={}){const r=s?.key===e,o=r?1===s.dir?"ascending":"descending":"none",n=r?1===s.dir?"▲":"▼":"⇅";return B`
    <th class="sortable ${a.numeric?"num":""}" aria-sort=${o}>
      <button
        type="button"
        class="sort-btn"
        title="Sort by ${t}"
        @click=${()=>i(function(t,e){return t?.key===e?{key:e,dir:1===t.dir?-1:1}:{key:e,dir:1}}(s,e))}
      >
        ${t}<span class="sort-arrow ${r?"active":""}" aria-hidden="true">${n}</span>
      </button>
    </th>
  `}t([ht({attribute:!1})],Ot.prototype,"hass",void 0),t([ht({type:Boolean})],Ot.prototype,"customizeMode",void 0),t([ut()],Ot.prototype,"_layout",void 0);let Mt=class extends Ot{constructor(){super(...arguments),this._users=[],this._risk={},this._loading=!0,this._error=null,this._busyUserId=null,this._sort=null,this._pwUserId=null,this._pwValue="",this._pwKeepSessions=!1,this._pwError=null,this._pwNotice=null,this._isOwner=!1}get viewId(){return"users"}connectedCallback(){super.connectedCallback(),this._load()}async _load(){this._loading=!0,this._error=null;try{const[t,e,s]=await Promise.all([_t(this.hass),vt(this.hass),Ct(this.hass).catch(()=>({is_owner:!1}))]);this._users=t,this._risk=e,this._isOwner=!!s.is_owner}catch(t){this._error=t?.message??String(t)}finally{this._loading=!1}}_adminTargetLocked(t){return!this._isOwner&&(t.is_owner||t.groups.includes("system-admin"))}_fmtDate(t){if(!t)return"never";return new Date(t).toLocaleString()}async _onDeactivate(t){if(confirm("Deactivate this user? All their sessions will be revoked.")){this._busyUserId=t;try{await((t,e)=>gt(t,{type:"ha_soc/users/deactivate",user_id:e}))(this.hass,t),await this._load()}finally{this._busyUserId=null}}}async _onRevokeAll(t){if(confirm("Revoke every interactive session for this user? Long-lived tokens are kept.")){this._busyUserId=t;try{await((t,e)=>gt(t,{type:"ha_soc/users/revoke_all_sessions",user_id:e}))(this.hass,t),await this._load()}finally{this._busyUserId=null}}}_onToggleResetPanel(t){this._pwUserId=this._pwUserId===t?null:t,this._pwValue="",this._pwKeepSessions=!1,this._pwError=null,this._pwNotice=null}async _onSubmitPassword(t){if(this._pwValue){this._busyUserId=t,this._pwError=null,this._pwNotice=null;try{const e=await((t,e,s,i)=>gt(t,{type:"ha_soc/users/set_password",user_id:e,password:s,revoke_sessions:i}))(this.hass,t,this._pwValue,!this._pwKeepSessions);this._pwNotice=e.sessions_revoked>0?`Password set. ${e.sessions_revoked} interactive session${1===e.sessions_revoked?"":"s"} revoked; long-lived tokens were kept.`:this._pwKeepSessions?"Password set. Existing sessions were kept at your request.":"Password set. No interactive sessions were active.",this._pwUserId=null,this._pwValue="",this._pwKeepSessions=!1}catch(t){this._pwError=t?.message??"Could not set the password."}finally{this._busyUserId=null}}}_renderPasswordPanel(t){return B`
      <tr>
        <td colspan="7" style="background:rgba(var(--rgb-primary-text-color,0,0,0),0.03);">
          <div style="display:flex;flex-direction:column;gap:8px;max-width:560px;">
            <div style="font-weight:600;font-size:13px;">
              Set a new password for ${t.name??t.id}
            </div>
            <div class="muted" style="font-size:12.5px;line-height:1.5;">
              Setting the password also revokes every interactive session this user
              holds, so anyone signed in with the old password is signed out
              immediately. Long-lived access tokens are kept either way. Owner-only
              action, recorded in the audit log.
            </div>
            <input
              type="password"
              autocomplete="new-password"
              placeholder="New password"
              style="max-width:280px;"
              .value=${this._pwValue}
              @input=${t=>this._pwValue=t.target.value}
            />
            <label
              style="display:inline-flex;align-items:center;gap:6px;font-size:12.5px;cursor:pointer;"
            >
              <input
                type="checkbox"
                .checked=${this._pwKeepSessions}
                @change=${t=>this._pwKeepSessions=t.target.checked}
              />
              Also keep this user's current sessions (not recommended: whoever holds
              the old password stays signed in)
            </label>
            ${this._pwError?B`<div style="color:var(--error-color,#db4437);font-size:12.5px;">
                  ${this._pwError}
                </div>`:W}
            <div class="toolbar" style="margin:0;">
              <button
                class="ha-btn"
                ?disabled=${!this._pwValue||this._busyUserId===t.id}
                @click=${()=>this._onSubmitPassword(t.id)}
              >
                ${this._busyUserId===t.id?"Setting…":"Set password"}
              </button>
              <button class="ha-btn" @click=${()=>this._onToggleResetPanel(t.id)}>Cancel</button>
            </div>
          </div>
        </td>
      </tr>
    `}render(){if(this._loading)return B`<div class="empty">Loading users…</div>`;if(this._error)return B`
        <div class="card" style="border:1px solid var(--error-color,#db4437);">
          <h3>Could not load Users &amp; Access</h3>
          <p style="font-size:13px;">${this._error}</p>
          <button class="ha-btn" @click=${()=>this._load()}>Retry</button>
        </div>
      `;if(!this._users.length)return B`<div class="empty">No users found.</div>`;const t=this._sort,e=t=>{this._sort=t},s=Dt(this._users,t,{user:t=>t.name??t.id,role:t=>`${t.is_admin?"Admin":"User"}${t.local_only?" · local only":""}`,mfa:t=>t.mfa_enabled,risk:t=>this._risk[t.id]?.score??null,last_login:t=>t.last_login_at?Date.parse(t.last_login_at):null,tokens:t=>t.llat_count}),i=[{id:"users",title:"Users & Access",hideable:!1,render:()=>B`
      <div class="card">
        <h3>Users &amp; Access</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Last login is derived from refresh-token activity — a background token
          refresh looks the same as a fresh interactive login. MFA status is read
          directly from the auth store but cannot be enforced by Home Assistant.
        </p>
        ${this._pwNotice?B`<p class="muted" style="font-size:12.5px;">${this._pwNotice}</p>`:W}
        <table>
          <thead>
            <tr>
              ${Ut("User","user",t,e)}
              ${Ut("Role","role",t,e)}
              ${Ut("MFA","mfa",t,e)}
              ${Ut("Risk","risk",t,e)}
              ${Ut("Last login","last_login",t,e)}
              ${Ut("Tokens","tokens",t,e)}
              <th></th>
            </tr>
          </thead>
          <tbody>
            ${s.map(t=>{const e=this._risk[t.id];return B`
                <tr class=${t.is_active?"":"row-disabled"}>
                  <td>
                    <div>${t.name??t.id}</div>
                    ${t.is_owner?B`<span class="tag enforced">owner</span>`:W}
                    ${t.is_active?W:B`<span class="tag cosmetic">deactivated</span>`}
                  </td>
                  <td>${t.is_admin?"Admin":"User"}${t.local_only?" · local only":""}</td>
                  <td>
                    ${t.mfa_enabled?B`<span class="pill good"><span class="dot"></span>enabled</span>`:!1===t.mfa_assessable?B`<span
                            class="muted"
                            title="Every credential this user has comes from an external auth provider (SSO/header proxy, trusted networks, or a command-line provider). Home Assistant cannot see a second factor enforced upstream, so MFA cannot be assessed for this account."
                            >not assessable</span
                          >`:B`<span class="pill high"><span class="dot"></span>none</span>`}
                  </td>
                  <td>
                    ${e?B`<span class="pill ${"critical"===e.band||"high"===e.band?"high":"moderate"===e.band?"medium":"good"}">
                          <span class="dot"></span>${e.score}
                        </span>`:B`<span class="muted">—</span>`}
                  </td>
                  <td>
                    <div>${this._fmtDate(t.last_login_at)}</div>
                    ${t.last_login_ip?B`<div class="muted">${t.last_login_ip}</div>`:W}
                  </td>
                  <td>
                    ${t.llat_count>0?B`<span class="chip">${t.llat_count} long-lived</span>`:B`<span class="muted">none</span>`}
                  </td>
                  <td>
                    <div class="toolbar" style="margin:0;">
                      <button
                        class="ha-btn"
                        ?disabled=${this._busyUserId===t.id||t.is_owner}
                        @click=${()=>this._onToggleResetPanel(t.id)}
                      >
                        ${this._pwUserId===t.id?"Close":"Reset password"}
                      </button>
                      <button
                        class="ha-btn"
                        ?disabled=${this._busyUserId===t.id||this._adminTargetLocked(t)}
                        title=${this._adminTargetLocked(t)?"This user is in the admin group; only the account owner can revoke an administrator's sessions.":""}
                        @click=${()=>this._onRevokeAll(t.id)}
                      >
                        Revoke sessions
                      </button>
                      <button
                        class="ha-btn danger"
                        ?disabled=${this._busyUserId===t.id||t.is_owner||this._adminTargetLocked(t)}
                        title=${this._adminTargetLocked(t)?"This user is in the admin group; only the account owner can deactivate an administrator.":""}
                        @click=${()=>this._onDeactivate(t.id)}
                      >
                        Deactivate
                      </button>
                    </div>
                  </td>
                </tr>
                ${this._pwUserId===t.id?this._renderPasswordPanel(t):W}
              `})}
          </tbody>
        </table>
      </div>
        `}];return this._renderSections(i)}};Mt.styles=Ft,t([ut()],Mt.prototype,"_users",void 0),t([ut()],Mt.prototype,"_risk",void 0),t([ut()],Mt.prototype,"_loading",void 0),t([ut()],Mt.prototype,"_error",void 0),t([ut()],Mt.prototype,"_busyUserId",void 0),t([ut()],Mt.prototype,"_sort",void 0),t([ut()],Mt.prototype,"_pwUserId",void 0),t([ut()],Mt.prototype,"_pwValue",void 0),t([ut()],Mt.prototype,"_pwKeepSessions",void 0),t([ut()],Mt.prototype,"_pwError",void 0),t([ut()],Mt.prototype,"_pwNotice",void 0),t([ut()],Mt.prototype,"_isOwner",void 0),Mt=t([dt("ha-soc-users-view")],Mt);const Ht=[["","All categories"],["service_call","Service call"],["login_ok","Login OK"],["login_fail","Login failed"],["token_created","Token created"],["session_seen","Session first seen"],["user_added","User added"],["user_updated","User updated"],["user_removed","User removed"],["lovelace_change","Dashboard edit"],["dashboard_panels_change","Panel set changed"],["entity_registry_change","Entity registry"],["device_registry_change","Device registry"],["area_registry_change","Area registry"],["floor_registry_change","Floor registry"],["label_registry_change","Label registry"],["category_registry_change","Category registry"],["config_entry_change","Config entry"],["core_config_change","Core config"],["watchdog_triggered","Watchdog triggered"],["soc_config_change","SOC config change"]];let Vt=class extends Ot{constructor(){super(...arguments),this._events=[],this._users=[],this._loading=!0,this._error=null,this._category="",this._userId="",this._verifyResult=null,this._sort=null,this._stats=null}get viewId(){return"audit"}connectedCallback(){super.connectedCallback(),this._loadUsers(),this._load()}async _loadUsers(){this._users=await _t(this.hass)}async _load(){this._loading=!0,this._error=null;try{this._events=await((t,e={})=>gt(t,{type:"ha_soc/audit/query",...e}).then(t=>t.events))(this.hass,{category:this._category||void 0,user_id:this._userId||void 0,limit:200})}catch(t){this._error=t?.message??String(t)}finally{this._loading=!1}}_nameFor(t){return t?this._users.find(e=>e.id===t)?.name??t:"—"}async _onVerify(){var t;this._verifyResult=await(t=this.hass,gt(t,{type:"ha_soc/audit/verify_chain"}))}async _onCategoryStats(){var t;this._stats=await(t=this.hass,gt(t,{type:"ha_soc/audit/category_stats"}))}_onCategoryChange(t){this._category=t.target.value,this._load()}_onUserChange(t){this._userId=t.target.value,this._load()}render(){const t=this._sort,e=t=>{this._sort=t},s=Dt(this._events,t,{time:t=>Date.parse(t.ts),category:t=>t.category,user:t=>t.user_id?this._nameFor(t.user_id):null,action:t=>t.domain?`${t.domain}.${t.service}${t.entity_ids?.length?` (${t.entity_ids.join(", ")})`:""}`:null,source:t=>t.ip}),i=[{id:"audit",title:"Audit Log",hideable:!1,render:()=>B`
      <div class="card">
        <h3>Audit Log</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Every user-attributed service call, user/dashboard change, and
          best-effort login signal. Failed logins carry only a source IP — Home
          Assistant never logs the attempted username on a failed login.
        </p>
        <div class="toolbar">
          <select @change=${this._onCategoryChange}>
            ${Ht.map(([t,e])=>B`<option value=${t} ?selected=${t===this._category}>${e}</option>`)}
          </select>
          <select @change=${this._onUserChange}>
            <option value="" ?selected=${""===this._userId}>All users</option>
            ${this._users.map(t=>B`<option value=${t.id} ?selected=${t.id===this._userId}>${t.name??t.id}</option>`)}
          </select>
          <span class="spacer"></span>
          <button class="ha-btn" @click=${this._onVerify}>Verify chain integrity</button>
          <button class="ha-btn" @click=${this._onCategoryStats}>Volume by category</button>
          <button class="ha-btn" @click=${this._load}>Refresh</button>
        </div>
        ${this._stats?B`<p class="muted" style="font-size:12px;">
              ${this._stats.day?B`${this._stats.day}: ${this._stats.total_records.toLocaleString()} records,
                  ${(this._stats.total_bytes/1024).toFixed(0)} KB.
                  ${this._stats.categories.slice(0,6).map(t=>`${t.category} ${t.records.toLocaleString()} (${Math.round(100*t.byte_share)}%)`).join(" · ")}${this._stats.categories.length>6?" · …":""}`:"No audit day files yet."}
            </p>`:null}
        ${this._verifyResult?B`<p class="${this._verifyResult.ok?"muted":""}" style="font-size:12.5px;">
              ${this._verifyResult.ok?(this._verifyResult.verified_from_seq??1)>1?`Chain intact - ${this._verifyResult.records_checked} records checked. Verified from record ${this._verifyResult.verified_from_seq}; records before ${this._verifyResult.expired_through??"the retention cutoff"} expired under retention.`:`Chain intact - ${this._verifyResult.records_checked} records checked.`:"Chain broken - see logs for the first mismatched record."}
            </p>`:null}
        ${this._loading?B`<div class="empty">Loading…</div>`:this._error?B`
              <div style="border:1px solid var(--error-color,#db4437);border-radius:6px;padding:10px 12px;">
                <p style="font-size:13px;margin:0 0 8px;">${this._error}</p>
                <button class="ha-btn" @click=${()=>this._load()}>Retry</button>
              </div>
            `:this._events.length?B`
              <table>
                <thead>
                  <tr>
                    ${Ut("Time","time",t,e)}
                    ${Ut("Category","category",t,e)}
                    ${Ut("User","user",t,e)}
                    ${Ut("Action","action",t,e)}
                    ${Ut("Source","source",t,e)}
                  </tr>
                </thead>
                <tbody>
                  ${s.map(t=>B`
                      <tr>
                        <td>${new Date(t.ts).toLocaleString()}</td>
                        <td><span class="tag cosmetic">${t.category}</span></td>
                        <td>${this._nameFor(t.user_id)}</td>
                        <td>${t.domain?`${t.domain}.${t.service}`:""} ${t.entity_ids?.length?`(${t.entity_ids.join(", ")})`:""}</td>
                        <td>${t.ip??"—"}</td>
                      </tr>
                    `)}
                </tbody>
              </table>
            `:B`<div class="empty">No matching events.</div>`}
      </div>
        `}];return this._renderSections(i)}};Vt.styles=Ft,t([ut()],Vt.prototype,"_events",void 0),t([ut()],Vt.prototype,"_users",void 0),t([ut()],Vt.prototype,"_loading",void 0),t([ut()],Vt.prototype,"_error",void 0),t([ut()],Vt.prototype,"_category",void 0),t([ut()],Vt.prototype,"_userId",void 0),t([ut()],Vt.prototype,"_verifyResult",void 0),t([ut()],Vt.prototype,"_sort",void 0),t([ut()],Vt.prototype,"_stats",void 0),Vt=t([dt("ha-soc-audit-view")],Vt);let Bt=class extends Ot{constructor(){super(...arguments),this._users=[],this._dashboards=[],this._selected=void 0,this._views=[],this._loading=!0,this._error=null,this._drift=[],this._viewsError=null,this._writeError=null,this._sort=null}get viewId(){return"permissions"}connectedCallback(){super.connectedCallback(),this._load()}async _load(){this._loading=!0,this._error=null;try{const[e,s]=await Promise.all([_t(this.hass),(t=this.hass,gt(t,{type:"ha_soc/permissions/dashboards/list"}).then(t=>t.dashboards))]);this._users=e.filter(t=>t.is_active),this._dashboards=s,void 0===this._selected&&s.length&&(this._selected=s[0].url_path??null),void 0!==this._selected&&await this._loadViews()}catch(t){this._error=t?.message??String(t)}finally{this._loading=!1}var t}async _loadViews(){this._viewsError=null;try{const s=await(t=this.hass,e=this._selected??null,gt(t,{type:"ha_soc/permissions/dashboard_config",url_path:e}).then(t=>t.config)),i=s?.views??[];this._views=i.map((t,e)=>({path:t.path??String(e),title:t.title??t.path??`View ${e+1}`,visibleUserIds:Array.isArray(t.visible)?t.visible.map(t=>t.user):null}))}catch(t){this._views=[],this._viewsError="not_found"===t?.code?"This dashboard has no saved layout yet — Home Assistant is showing an auto-generated default until someone opens and customizes it in the dashboard editor. There's nothing here for the permissions matrix to manage until then.":`Could not load this dashboard's views: ${t?.message??t}`}var t,e}async _onSelectDashboard(t){const e=t.target.value;this._selected="__default__"===e?null:e,await this._loadViews()}async _onToggleUser(t,e,s){const i=t.target,a=e.visibleUserIds??this._users.map(t=>t.id),r=a.includes(s),o=r?a.filter(t=>t!==s):[...a,s],n=o.length===this._users.length?[]:o;this._writeError=null;try{await((t,e,s,i)=>gt(t,{type:"ha_soc/permissions/view_visibility/set",url_path:e,view_path:s,user_ids:i}))(this.hass,this._selected??null,e.path,n),await this._loadViews()}catch(t){i.checked=r,this._writeError=`The visibility change for "${e.title}" was rejected: ${t?.message??t?.code??"unknown error"}. The checkbox was restored to the saved state.`}}async _onToggleFlag(t,e,s,i){const a=t.target;this._writeError=null;try{await((t,e,s)=>gt(t,{type:"ha_soc/permissions/dashboard_flags/set",dashboard_id:e,...s}))(this.hass,e,{[s]:i}),await this._load()}catch(t){a.checked=!i,this._writeError=`The ${s} change was rejected: ${t?.message??t?.code??"unknown error"}. The checkbox was restored to the saved state.`}}async _onCheckDrift(){this._writeError=null;try{this._drift=await(t=this.hass,gt(t,{type:"ha_soc/permissions/drift/check"}).then(t=>t.drift))}catch(t){this._writeError=`Drift check failed: ${t?.message??t}`}var t}render(){if(this._loading)return B`<div class="empty">Loading dashboards…</div>`;if(this._error)return B`
        <div class="card" style="border:1px solid var(--error-color,#db4437);">
          <h3>Could not load the Permissions Matrix</h3>
          <p style="font-size:13px;">${this._error}</p>
          <button class="ha-btn" @click=${()=>this._load()}>Retry</button>
        </div>
      `;const t=this._dashboards.find(t=>(t.url_path??null)===(this._selected??null)),e=[{id:"permissions",title:"Permissions Matrix",hideable:!1,render:()=>B`
      <div class="card">
        <h3>Permissions Matrix</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          <span class="tag cosmetic">UI-only</span> View/card visibility and
          <code>require_admin</code> change what a user's own frontend renders — any
          authenticated user can still fetch a dashboard's full config over the
          websocket API. The only real access-control lever is a user's
          admin/non-admin group, managed in the Users &amp; Access tab.
        </p>
        <div class="toolbar">
          <select .value=${this._selected??"__default__"} @change=${this._onSelectDashboard}>
            ${this._dashboards.map(t=>B`<option value=${t.url_path??"__default__"}>
                  ${t.title??t.url_path??"Overview"}
                </option>`)}
          </select>
          ${t?B`
                <label style="font-size:12.5px;display:flex;align-items:center;gap:4px;">
                  <input
                    type="checkbox"
                    .checked=${!!t.require_admin}
                    @change=${e=>this._onToggleFlag(e,t.id,"require_admin",e.target.checked)}
                  />
                  require_admin
                </label>
                <label style="font-size:12.5px;display:flex;align-items:center;gap:4px;">
                  <input
                    type="checkbox"
                    .checked=${!1!==t.show_in_sidebar}
                    @change=${e=>this._onToggleFlag(e,t.id,"show_in_sidebar",e.target.checked)}
                  />
                  show in sidebar
                </label>
              `:W}
          <span class="spacer"></span>
          <button class="ha-btn" @click=${this._onCheckDrift}>Check drift</button>
        </div>

        ${this._writeError?B`<p style="font-size:12.5px;color:var(--error-color,#db4437);">
              ${this._writeError}
            </p>`:W}
        ${this._drift.length?B`<p style="font-size:12.5px;color:var(--warning-color);">
              ${this._drift.length} view(s) no longer match the policy last applied here — likely edited directly in the dashboard editor.
            </p>`:W}

        ${this._views.length?(()=>{const t={view:t=>t.title};for(const e of this._users)t[`user:${e.id}`]=t=>null===t.visibleUserIds||t.visibleUserIds.includes(e.id);const e=Dt(this._views,this._sort,t),s=this._sort,i=t=>this._sort=t;return B`
              <table>
                <thead>
                  <tr>
                    ${Ut("View","view",s,i)}
                    ${this._users.map(t=>Ut(t.name??t.id,`user:${t.id}`,s,i))}
                  </tr>
                </thead>
                <tbody>
                  ${e.map(t=>B`
                      <tr>
                        <td>${t.title}</td>
                        ${this._users.map(e=>{const s=null===t.visibleUserIds||t.visibleUserIds.includes(e.id);return B`
                            <td>
                              <input
                                type="checkbox"
                                .checked=${s}
                                @change=${s=>this._onToggleUser(s,t,e.id)}
                              />
                            </td>
                          `})}
                      </tr>
                    `)}
                </tbody>
              </table>
            `})():B`<div class="empty">
              ${this._viewsError??"This dashboard has no views, or is YAML-managed (read-only)."}
            </div>`}
      </div>
        `}];return this._renderSections(e)}};var jt;Bt.styles=Ft,t([ut()],Bt.prototype,"_users",void 0),t([ut()],Bt.prototype,"_dashboards",void 0),t([ut()],Bt.prototype,"_selected",void 0),t([ut()],Bt.prototype,"_views",void 0),t([ut()],Bt.prototype,"_loading",void 0),t([ut()],Bt.prototype,"_error",void 0),t([ut()],Bt.prototype,"_drift",void 0),t([ut()],Bt.prototype,"_viewsError",void 0),t([ut()],Bt.prototype,"_writeError",void 0),t([ut()],Bt.prototype,"_sort",void 0),Bt=t([dt("ha-soc-permissions-view")],Bt);const Wt=["new","confirmed","dismissed","resolved"],qt=["critical","high","medium","low","info"];function Kt(t){const e=qt.indexOf(t);return-1===e?qt.length:e}function Gt(t,e){const s=t.indexOf(String(e));return-1===s?null:s}const Zt=["high","medium","advisory"],Jt=["exact_cpe","curated_map","keyword","heuristic"];function Yt(t){return"4"===t?"IPv4":"6"===t?"IPv6":"IPv4+IPv6"}function Qt(t){return t?t.includes(":")?"6":"4":null}function Xt(t){return"0.0.0.0"===t?{priority:0,label:"all interfaces",cls:"high"}:t?t.startsWith("127.")||t.startsWith("169.254.")?{priority:3,label:"loopback / link-local",cls:"good"}:function(t){const e=t.match(/^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/);if(!e)return!1;const[s,i]=[Number(e[1]),Number(e[2])];return 10===s||172===s&&i>=16&&i<=31||192===s&&168===i}(t)?{priority:2,label:"private (RFC 1918)",cls:"low"}:{priority:1,label:"public / routable",cls:"high"}:{priority:4,label:"unresolved (IPv6)",cls:"info"}}let te=jt=class extends Ot{constructor(){super(...arguments),this._scannerFindings=[],this._coverage=null,this._vulnFindings=[],this._misconfigFindings=[],this._probe=null,this._loading=!0,this._error=null,this._scanning=!1,this._scanError=null,this._exportNotice=null,this._firewall=null,this._fwDraftRules=[{action:"allow",proto:"tcp",port:0,source:"",family:"both"}],this._fwBackupAck=!1,this._fwSubmitting=!1,this._fwError=null,this._fwPollHandle=null,this._isOwner=!1,this._misconfigSort=null,this._scannerSort=null,this._vulnSort=null,this._portSort=null,this._fwRulesSort=null,this._coverageSort=null}get viewId(){return"scanner"}connectedCallback(){super.connectedCallback(),this._load()}disconnectedCallback(){super.disconnectedCallback(),null!==this._fwPollHandle&&(window.clearInterval(this._fwPollHandle),this._fwPollHandle=null)}async _load(){this._loading=!0,this._error=null;try{const[e,s,i,a,r]=await Promise.all([(t=this.hass,gt(t,{type:"ha_soc/scanner/list"})),ft(this.hass),xt(this.hass),At(this.hass),Ct(this.hass).catch(()=>({is_owner:!1}))]);this._scannerFindings=e.findings,this._coverage=e.coverage??null,this._vulnFindings=s,this._misconfigFindings=i.misconfig_findings,this._probe=a,this._isOwner=!!r.is_owner,this._firewall=this._isOwner?await Pt(this.hass).catch(()=>null):null,this._maybeManageFirewallPolling()}catch(t){this._error=t?.message??String(t)}finally{this._loading=!1}var t}_maybeManageFirewallPolling(){const t=null!=this._firewall?.pending;t&&null===this._fwPollHandle?this._fwPollHandle=window.setInterval(()=>this._pollFirewallStatus(),2e3):t||null===this._fwPollHandle||(window.clearInterval(this._fwPollHandle),this._fwPollHandle=null)}async _pollFirewallStatus(){this._applyFirewallStatus(await Pt(this.hass))}_applyFirewallStatus(t){const e=null!=this._firewall?.pending;this._firewall=t,e&&!t.pending&&(this._fwBackupAck=!1),this._maybeManageFirewallPolling()}_fwRuleValid(t){const e=t.family??"both",s=Qt(t.source??"");return Number.isInteger(t.port)&&t.port>=1&&t.port<=65535&&("allow"===t.action||"deny"===t.action)&&("tcp"===t.proto||"udp"===t.proto)&&("4"===e||"6"===e||"both"===e)&&(null===s||s===e)}_fwUpdateRule(t,e){this._fwDraftRules=this._fwDraftRules.map((s,i)=>i===t?{...s,...e}:s)}_fwAddRule(){this._fwDraftRules=[...this._fwDraftRules,{action:"allow",proto:"tcp",port:0,source:"",family:"both"}]}_fwRemoveRule(t){this._fwDraftRules=this._fwDraftRules.filter((e,s)=>s!==t)}async _onProposeTest(){this._fwError=null,this._fwSubmitting=!0;try{const t=this._fwDraftRules.map(t=>({action:t.action,proto:t.proto,port:t.port,source:t.source?t.source:null,family:t.family??"both"}));await((t,e,s)=>gt(t,{type:"ha_soc/firewall/test",rules:e,backup_acknowledged:s}))(this.hass,t,this._fwBackupAck),this._applyFirewallStatus(await Pt(this.hass))}catch(t){this._fwError=t?.message??"Failed to propose the firewall change."}finally{this._fwSubmitting=!1}}async _onConfirmTest(){if(this._firewall?.pending){this._fwError=null,this._fwSubmitting=!0;try{await(t=this.hass,e=this._firewall.pending.test_id,gt(t,{type:"ha_soc/firewall/confirm",test_id:e})),this._applyFirewallStatus(await Pt(this.hass))}catch(t){this._fwError=t?.message??"Failed to confirm the firewall change."}finally{this._fwSubmitting=!1}var t,e}}async _onCancelTest(){if(this._firewall?.pending){this._fwError=null,this._fwSubmitting=!0;try{await(t=this.hass,e=this._firewall.pending.test_id,gt(t,{type:"ha_soc/firewall/cancel",test_id:e})),this._applyFirewallStatus(await Pt(this.hass))}catch(t){this._fwError=t?.message??"Failed to cancel the firewall change."}finally{this._fwSubmitting=!1}var t,e}}async _onDiscardPending(){if(!this._firewall?.pending)return;if(confirm("Discard this unreported firewall test?\n\nThe add-on never reported its outcome, so HA SOC does not know what is live on the host. The record is archived as 'discarded_unreported' and new tests become possible again. Nothing is changed on the host by discarding.")){this._fwError=null,this._fwSubmitting=!0;try{await(t=this.hass,gt(t,{type:"ha_soc/firewall/discard_pending"})),this._applyFirewallStatus(await Pt(this.hass))}catch(t){this._fwError=t?.message??"Failed to discard the pending firewall test."}finally{this._fwSubmitting=!1}var t}}async _onScanIntegrations(){this._scanning=!0,this._scanError=null;try{await(t=this.hass,gt(t,{type:"ha_soc/scanner/scan_now",domain:e})),await this._load()}catch(t){this._scanError=`Integration scan failed: ${t?.message??t}`}finally{this._scanning=!1}var t,e}async _onScanVulns(){this._scanning=!0,this._scanError=null;try{await(t=this.hass,gt(t,{type:"ha_soc/vulns/scan_now"}).then(t=>t.findings)),await this._load()}catch(t){this._scanError=`Device vulnerability scan failed: ${t?.message??t}`}finally{this._scanning=!1}var t}async _onVulnStatus(t,e){this._scanError=null;try{await((t,e,s,i)=>gt(t,{type:"ha_soc/vulns/set_status",finding_id:e,status:s,note:i}))(this.hass,t,e)}catch(t){this._scanError=`Status change failed: ${t?.message??t}`}await this._load()}async _onExportFinding(t){if(confirm(`Copy a GHSA-shaped advisory draft to the clipboard?\n\nIntegration: ${t.domain}\nMatched code: ${t.snippet}\n\nNothing is submitted anywhere. The text is only placed on your clipboard for you to review and paste yourself.`)){this._exportNotice=null;try{const i=await(e=this.hass,s=t.id,gt(e,{type:"ha_soc/scanner/export",finding_id:s})),a=[`Title: ${i.title}`,`Severity: ${i.severity}`,`CWE: ${i.cwe}`,`Package: ${i.affected.package} (${i.affected.ecosystem})`,"",i.description].join("\n");await navigator.clipboard.writeText(a),this._exportNotice=`Copied the advisory draft for ${t.domain} (${t.file}:${t.line}) to the clipboard.`}catch(t){this._exportNotice=`Export failed: ${t?.message??"could not copy to the clipboard"}`}var e,s}}async _onMisconfigStatus(t,e){this._scanError=null;try{await((t,e,s,i)=>gt(t,{type:"ha_soc/misconfig/set_status",finding_id:e,status:s,note:i}))(this.hass,t,e)}catch(t){this._scanError=`Status change failed: ${t?.message??t}`}await this._load()}_groupedVulnFindings(){const t=new Map;for(const e of this._vulnFindings){const s=String(e.device_name??"Unknown device"),i=t.get(s);i?i.push(e):t.set(s,[e])}const e=this._vulnSort,s=Array.from(t.entries()).map(([t,s])=>({device_name:t,worst:Math.min(...s.map(t=>Kt(t.severity))),findings:e?Dt(s,e,jt.VULN_SORT):[...s].sort((t,e)=>Kt(t.severity)-Kt(e.severity))}));return"cve"===e?.key?s.sort((t,s)=>t.device_name.localeCompare(s.device_name,void 0,{sensitivity:"base",numeric:!0})*e.dir):s.sort((t,e)=>t.worst-e.worst),s}_renderScannerCoverage(){if(!this._coverage)return W;const t=new Set(Object.keys(this._coverage)),e=new Set(this._scannerFindings.map(t=>String(t.domain))),s=Array.from(e).filter(e=>!t.has(e)).sort((t,e)=>t.localeCompare(e)),i=Object.entries(this._coverage).map(([t,e])=>({domain:t,cov:e})),a=this._coverageSort?Dt(i,this._coverageSort,jt.COVERAGE_SORT):i.slice().sort((t,e)=>t.domain.localeCompare(e.domain));return B`
      <h4 class="fw-subhead">Scan coverage</h4>
      <p class="muted" style="font-size:12px;margin-top:-6px;">
        What the most recent completed pass over each domain actually looked at.
        A domain is never implied clean by an absent record.
      </p>
      ${i.length?B`
            <table>
              <thead>
                <tr>
                  ${Ut("Domain","domain",this._coverageSort,t=>this._coverageSort=t)}
                  ${Ut("Files scanned","files",this._coverageSort,t=>this._coverageSort=t,{numeric:!0})}
                  ${Ut("Skipped (too large)","oversize",this._coverageSort,t=>this._coverageSort=t,{numeric:!0})}
                  ${Ut("Skipped (over cap)","over_cap",this._coverageSort,t=>this._coverageSort=t,{numeric:!0})}
                  ${Ut("Parse failures","parse_failures",this._coverageSort,t=>this._coverageSort=t,{numeric:!0})}
                  ${Ut("Scanned at","scanned_at",this._coverageSort,t=>this._coverageSort=t)}
                </tr>
              </thead>
              <tbody>
                ${a.map(t=>B`
                    <tr>
                      <td>${t.domain}</td>
                      <td class="num">${t.cov.scanned_files}</td>
                      <td class="num">${t.cov.skipped_oversize}</td>
                      <td class="num">${t.cov.skipped_over_cap}</td>
                      <td class="num">${t.cov.parse_failures}</td>
                      <td>${new Date(t.cov.scanned_at).toLocaleString()}</td>
                    </tr>
                  `)}
              </tbody>
            </table>
          `:B`<div class="empty">No domain has completed a scan yet.</div>`}
      ${s.length?B`<p style="font-size:12.5px;margin-top:8px;">
            <strong>Not scanned this pass:</strong> ${s.join(", ")}.
            ${1===s.length?"Its":"Their"} existing findings above were not
            re-verified in the most recent run.
          </p>`:W}
    `}_renderStatusSelect(t,e,s){return B`
      <select @change=${t=>s(t.target.value)}>
        ${Wt.map(t=>B`<option value=${t} ?selected=${t===e}>${t}</option>`)}
      </select>
    `}_sortedMisconfigFindings(){return this._misconfigSort?Dt(this._misconfigFindings,this._misconfigSort,jt.MISCONFIG_SORT):[...this._misconfigFindings].sort((t,e)=>Kt(t.severity)-Kt(e.severity))}render(){if(this._loading)return B`<div class="empty">Loading findings…</div>`;if(this._error)return B`
        <div class="card" style="border:1px solid var(--error-color,#db4437);">
          <h3>Could not load the Scanner tab</h3>
          <p style="font-size:13px;">${this._error}</p>
          <button class="ha-btn" @click=${()=>this._load()}>Retry</button>
        </div>
      `;const t=[{id:"misconfig",title:"Misconfiguration Findings",render:()=>B`
      <div class="card">
        <h3>Misconfiguration Findings</h3>
        ${this._misconfigFindings.length?B`
              <table>
                <thead>
                  <tr>
                    ${Ut("Check","check",this._misconfigSort,t=>this._misconfigSort=t)}
                    ${Ut("Severity","severity",this._misconfigSort,t=>this._misconfigSort=t)}
                    ${Ut("Summary","summary",this._misconfigSort,t=>this._misconfigSort=t)}
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  ${this._sortedMisconfigFindings().map(t=>B`
                      <tr>
                        <td>${t.check}</td>
                        <td><span class="pill ${t.severity}"><span class="dot"></span>${t.severity}</span></td>
                        <td>${t.summary}</td>
                        <td>
                          ${t.acknowledged_by_design?B`<span class="tag enforced" title=${t.acknowledged_reason??"Acknowledged by design"}
                                >acknowledged by design</span
                              >`:this._renderStatusSelect(t.id,t.status,e=>this._onMisconfigStatus(t.id,e))}
                        </td>
                      </tr>
                    `)}
                </tbody>
              </table>
            `:B`<div class="empty">No findings.</div>`}
      </div>
        `},{id:"integration_scanner",title:"Integration Security Scanner",render:()=>B`
      <div class="card">
        <h3>Integration Security Scanner</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Static AST/regex analysis of every installed integration's source — core and
          custom. Every finding is advisory and needs a human to confirm; Home
          Assistant's own quality tooling (hassfest) never checks for these patterns and
          never runs against custom_components at all. These rules find unobfuscated
          pattern instances only; a dynamically constructed call, a string-built
          decorator, or a renamed import will not be detected.
        </p>
        <div class="toolbar">
          <button class="ha-btn" ?disabled=${this._scanning} @click=${this._onScanIntegrations}>
            Scan all integrations now
          </button>
        </div>
        ${this._scannerFindings.length?B`
              <table>
                <thead>
                  <tr>
                    ${Ut("Domain","domain",this._scannerSort,t=>this._scannerSort=t)}
                    ${Ut("Pattern","pattern",this._scannerSort,t=>this._scannerSort=t)}
                    ${Ut("Location","location",this._scannerSort,t=>this._scannerSort=t)}
                    ${Ut("Confidence","confidence",this._scannerSort,t=>this._scannerSort=t)}
                    ${Ut("CWE","cwe",this._scannerSort,t=>this._scannerSort=t)}
                    <th>Status</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  ${Dt(this._scannerFindings,this._scannerSort,jt.SCANNER_SORT).map(t=>B`
                      <tr>
                        <td>${t.domain}</td>
                        <td><span class="pill ${t.severity}"><span class="dot"></span>${t.pattern}</span></td>
                        <td>${t.file}:${t.line}</td>
                        <td>${t.confidence}</td>
                        <td>${t.cwe}</td>
                        <td>${this._renderStatusSelect(t.id,t.status,e=>this._onVulnStatus(t.id,e))}</td>
                        <td><button class="ha-btn" @click=${()=>this._onExportFinding(t)}>Export</button></td>
                      </tr>
                    `)}
                </tbody>
              </table>
              ${this._exportNotice?B`<p class="muted" style="font-size:12px;margin:6px 0 0;">${this._exportNotice}</p>`:W}
            `:B`<div class="empty">No findings.</div>`}
        ${this._renderScannerCoverage()}
      </div>
        `},{id:"device_vulns",title:"Device Vulnerabilities",render:()=>B`
      <div class="card">
        <h3>Device Vulnerabilities</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Matches monitored devices against NVD by manufacturer/model — a heuristic
          match, never a confirmed exploit. Absence of a match is not evidence a device
          is secure.
        </p>
        <div class="toolbar">
          <button class="ha-btn" ?disabled=${this._scanning} @click=${this._onScanVulns}>
            Scan devices now
          </button>
        </div>
        ${this._vulnFindings.length?B`
              <table>
                <thead>
                  <tr>
                    ${Ut("CVE","cve",this._vulnSort,t=>this._vulnSort=t)}
                    ${Ut("CVSS","cvss",this._vulnSort,t=>this._vulnSort=t)}
                    ${Ut("Confidence","confidence",this._vulnSort,t=>this._vulnSort=t)}
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  ${this._groupedVulnFindings().map(t=>B`
                      <tr>
                        <td colspan="4" style="font-weight:600;background:rgba(var(--rgb-primary-text-color,0,0,0),0.04);">
                          ${t.device_name}
                          <span class="muted" style="font-weight:400;font-size:11.5px;"
                            >(${t.findings.length} finding${1===t.findings.length?"":"s"})</span
                          >
                        </td>
                      </tr>
                      ${t.findings.map(t=>B`
                          <tr>
                            <td>${t.cve_id??"—"}</td>
                            <td><span class="pill ${t.severity}"><span class="dot"></span>${t.cvss??"unscored"}</span></td>
                            <td>${t.confidence}</td>
                            <td>${this._renderStatusSelect(t.id,t.status,e=>this._onVulnStatus(t.id,e))}</td>
                          </tr>
                        `)}
                    `)}
                </tbody>
              </table>
            `:B`<div class="empty">No findings.</div>`}
      </div>
        `},{id:"host_probe",title:"Host Probe",render:()=>this._renderProbeCard()},{id:"firewall_rules",title:"Firewall Rules",render:()=>this._renderFirewallCard()}];return B`
      ${this._scanError?B`<div class="card" style="border:1px solid var(--error-color,#db4437);">
            <p style="font-size:13px;color:var(--error-color,#db4437);margin:0;">${this._scanError}</p>
          </div>`:W}
      ${this._renderSections(t)}
    `}_renderProbeCard(){const t=this._probe;if(!t)return W;if(!t.supervisor)return B`
        <div class="card">
          <h3>Host Probe <span class="tag cosmetic">not available</span></h3>
          <p class="muted" style="font-size:12.5px;">
            Real socket-level port scanning of the host needs a companion add-on with
            host-network access — something a Python integration structurally cannot do
            on its own, even on Home Assistant OS. This install isn't running under
            Supervisor (Core/Container), so this feature has nothing to attach to here.
          </p>
        </div>
      `;if(!t.installed)return B`
        <div class="card">
          <h3>Host Probe <span class="tag cosmetic">not installed</span></h3>
          <p class="muted" style="font-size:12.5px;">
            The optional <strong>HA SOC Probe</strong> add-on isn't installed. It's the
            only way to see the host's actual listening ports — this integration alone
            can't reach past its own container. Add its repository under
            Settings → Add-ons → Add-on Store → ⋮ → Repositories, then install
            "HA SOC Probe". See the README for the exact URL.
          </p>
        </div>
      `;const e=t.result;return B`
      <div class="card">
        <h3>
          Host Probe
          <span class="tag ${t.running?"enforced":"cosmetic"}">
            ${t.running?"running":"installed, not running"}
          </span>
          ${t.update_available?B`<span class="tag cosmetic">update available</span>`:W}
        </h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Version ${t.version??"unknown"}. Reports the host's real listening TCP
          ports — process-name attribution isn't included: identifying which process
          owns a port needs the add-on to also see the host's process list
          (<code>host_pid</code>), a privilege this add-on deliberately doesn't request.
        </p>
        ${e?B`
              <p class="muted" style="font-size:12px;">
                Last reported ${new Date(e.reported_at).toLocaleString()}
              </p>
              ${e.open_ports.length?this._renderPortsByBindAddress(e.open_ports):B`<div class="empty">No listening ports reported.</div>`}
            `:B`<div class="empty">No scan reported yet.</div>`}
      </div>
    `}_fwRuleCoveringPort(t){const e=this._firewall?.known_rules;if(!e?.length)return null;const s=t.address?"4":"6",i=e.filter(e=>{const i=e.family??"both";return e.port===t.port&&e.proto===t.proto&&("both"===i||i===s)});return i.length?(i.sort((t,e)=>t.action!==e.action?"deny"===t.action?-1:1:(t.source?1:0)-(e.source?1:0)),i[0]):null}_renderPortRuleCell(t){const e=this._fwRuleCoveringPort(t),s=t.address?"":" IPv6 bind addresses are not decoded by the add-on, so this correlation is by port and protocol only.";if(!e)return B`<td class="muted"><span title=${"No HA_SOC_RULES entry matches this port and protocol for this listener's address family."+s}>no rule</span></td>`;const i=e.source?`from ${e.source}`:"any source";return B`
      <td>
        <span
          class="pill ${"allow"===e.action?"good":"critical"}"
          title=${`Covered by the ${e.action} ${e.proto}/${e.port} rule (${Yt(e.family)}, ${i}).`+(e.source?" Source-scoped: traffic from other sources is not affected by it.":"")+s}
          ><span class="dot"></span>${e.action}${t.address?"":" (by port)"}</span
        >
      </td>
    `}_renderPortsByBindAddress(t){const e=new Map;for(const s of t){const t=s.address??"__unresolved__",i=e.get(t);i?i.push(s):e.set(t,[s])}const s=Array.from(e.entries()).sort((t,e)=>{const s=Xt("__unresolved__"===t[0]?null:t[0]),i=Xt("__unresolved__"===e[0]?null:e[0]);return s.priority!==i.priority?s.priority-i.priority:t[0].localeCompare(e[0])}),i=!!this._firewall?.known_rules?.length,a=i?4:3;return B`
      <table>
        <thead>
          <tr>
            ${Ut("Port","port",this._portSort,t=>this._portSort=t)}
            ${Ut("Protocol","proto",this._portSort,t=>this._portSort=t)}
            ${Ut("Interface","interface",this._portSort,t=>this._portSort=t)}
            ${i?B`<th>Covered by rule</th>`:W}
          </tr>
        </thead>
        ${s.map(([t,e])=>{const s="__unresolved__"===t?null:t,r=Xt(s);return B`
            <tbody>
              <tr>
                <td colspan=${a} style="background:rgba(var(--rgb-primary-text-color,0,0,0),0.04);">
                  <strong>${s??"unresolved (IPv6)"}</strong>
                  <span class="pill ${r.cls}" style="margin-left:8px;"
                    ><span class="dot"></span>${r.label}</span
                  >
                  <span class="muted" style="margin-left:8px;font-size:12px;"
                    >${e.length} port${1===e.length?"":"s"}</span
                  >
                </td>
              </tr>
              ${(this._portSort?Dt(e,this._portSort,jt.PORT_SORT):e.slice().sort((t,e)=>t.port-e.port)).map(t=>B`
                    <tr>
                      <td>${t.port}</td>
                      <td>${t.proto}</td>
                      <td>
                        ${"(all interfaces)"===t.interface?B`<span class="pill high"><span class="dot"></span>all interfaces</span>`:B`<span class="muted">${t.interface??"—"}</span>`}
                      </td>
                      ${i?this._renderPortRuleCell(t):W}
                    </tr>
                  `)}
            </tbody>
          `})}
      </table>
    `}_renderFamilyCell(t){return B`
      <td>
        ${Yt(t.family)}
        ${t.partially_applied?B`<span
              class="pill high"
              style="margin-left:6px;"
              title="The host kernel does not support ip6tables, so the IPv6 half of this rule is not applied. Only its IPv4 half (if any) is live."
              ><span class="dot"></span>IPv6 not applied</span
            >`:W}
      </td>
    `}_renderLastOutcomeReason(t){const e=t.history.length?t.history[t.history.length-1]:null;return e?.reason?B`
      <p style="color:var(--error-color,#db4437);font-size:12.5px;margin:8px 0 0;">
        Last test (${e.test_id.slice(0,8)}) ended ${e.status}: ${e.reason}
      </p>
    `:W}_renderFirewallCard(){const t=this._probe,e=this._firewall;return t?.supervisor&&t?.installed?this._isOwner?e?B`
      <div class="card">
        <h3>Firewall Rules</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Reads, and — if you propose a change — writes the host's firewall via the HA
          SOC Probe add-on's <code>NET_ADMIN</code> capability. Every proposed change is
          backed up first and applied to a dedicated chain this project owns outright,
          never the host's raw INPUT chain. An unconfirmed change reverts itself
          automatically once its test window closes. Rules are dual-stack by default:
          a rule with no source applies to IPv4 and IPv6 alike, and a source address
          pins the rule to that address's own family.
        </p>
        ${!1===e.ipv6_supported?B`
              <p
                style="color:var(--error-color,#db4437);font-size:12.5px;border:1px solid var(--error-color,#db4437);border-radius:4px;padding:8px 10px;"
              >
                IPv6 rules not applied: the host kernel does not support ip6tables.
                Rules with family IPv6 are not live at all, and dual-stack rules are
                live for IPv4 only.
              </p>
            `:W}

        <h4 class="fw-subhead">Active rules</h4>
        ${e.known_rules&&e.known_rules.length?B`
              <table>
                <thead>
                  <tr>
                    ${Ut("Action","action",this._fwRulesSort,t=>this._fwRulesSort=t)}
                    ${Ut("Protocol","proto",this._fwRulesSort,t=>this._fwRulesSort=t)}
                    ${Ut("Port","port",this._fwRulesSort,t=>this._fwRulesSort=t)}
                    ${Ut("Source","source",this._fwRulesSort,t=>this._fwRulesSort=t)}
                    ${Ut("Family","family",this._fwRulesSort,t=>this._fwRulesSort=t)}
                  </tr>
                </thead>
                <tbody>
                  ${Dt(e.known_rules,this._fwRulesSort,jt.FW_RULE_SORT).map(t=>B`
                      <tr>
                        <td>
                          <span class="pill ${"allow"===t.action?"good":"critical"}"
                            ><span class="dot"></span>${t.action}</span
                          >
                        </td>
                        <td>${t.proto}</td>
                        <td>${t.port}</td>
                        <td class="muted">${t.source??"any"}</td>
                        ${this._renderFamilyCell(t)}
                      </tr>
                    `)}
                </tbody>
              </table>
            `:B`<div class="empty">
              No rules reported yet${null===e.known_rules?" — waiting for the add-on's first report.":"."}
            </div>`}
        ${e.known_rules_reported_at?B`<p class="muted" style="font-size:11.5px;margin:6px 0 0;">
              Last reported ${new Date(e.known_rules_reported_at).toLocaleString()}
            </p>`:W}
        ${this._renderLastOutcomeReason(e)}
        ${e.pending?B`
              ${this._renderFirewallPending(e.pending)}
              ${this._renderFirewallBuilder("A proposed change is still pending. A new test can only be proposed once the add-on has reported the outcome of the current one.")}
            `:this._renderFirewallBuilder(null)}
        ${this._fwError?B`<p style="color:var(--error-color,#db4437);font-size:12.5px;margin-top:10px;">${this._fwError}</p>`:W}
      </div>
    `:W:B`
        <div class="card">
          <h3>Firewall Rules <span class="tag cosmetic">owner only</span></h3>
          <p class="muted" style="font-size:12.5px;">
            The firewall is available to the account owner only.
          </p>
        </div>
      `:W}_renderFirewallPending(t){const e=Math.max(0,Math.round((new Date(t.expires_at).getTime()-Date.now())/1e3)),s=Date.now()>=new Date(t.expires_at).getTime(),i={testing:t.applied_at?"Testing — live on the host":"Queued — waiting for the add-on to apply",confirmed:"Confirmed — waiting for the add-on to acknowledge",reverted:"Reverting — waiting for the add-on to acknowledge",expired_unreported:"Window expired, the add-on has not confirmed the revert yet",expired:"Window expired, the add-on has not confirmed the revert yet"};return B`
      <h4 class="fw-subhead">Proposed rules — ${i[t.status]??t.status}</h4>
      <table>
        <thead>
          <tr>
            <th>Action</th>
            <th>Protocol</th>
            <th>Port</th>
            <th>Source</th>
            <th>Family</th>
          </tr>
        </thead>
        <tbody>
          ${t.proposed_rules.map(t=>B`
              <tr>
                <td>
                  <span class="pill ${"allow"===t.action?"good":"critical"}"
                    ><span class="dot"></span>${t.action}</span
                  >
                </td>
                <td>${t.proto}</td>
                <td>${t.port}</td>
                <td class="muted">${t.source??"any"}</td>
                ${this._renderFamilyCell(t)}
              </tr>
            `)}
        </tbody>
      </table>
      <div class="toolbar" style="margin-top:12px;">
        <button
          class="ha-btn"
          ?disabled=${this._fwSubmitting||"testing"!==t.status}
          @click=${this._onConfirmTest}
        >
          Apply${"testing"===t.status?B` (${e}s to auto-revert)`:W}
        </button>
        <button
          class="ha-btn danger"
          ?disabled=${this._fwSubmitting||"testing"!==t.status}
          @click=${this._onCancelTest}
        >
          Cancel now
        </button>
        ${s?B`
              <button
                class="ha-btn danger"
                ?disabled=${this._fwSubmitting}
                title="The add-on never reported this test's outcome. Discard archives it as 'discarded_unreported' so a new test can be proposed; nothing on the host is changed."
                @click=${this._onDiscardPending}
              >
                Discard unreported test
              </button>
            `:W}
      </div>
    `}_renderFirewallBuilder(t){const e=null===t&&this._fwBackupAck&&this._fwDraftRules.length>0&&this._fwDraftRules.every(t=>this._fwRuleValid(t));return B`
      <h4 class="fw-subhead">Propose a change</h4>
      <table>
        <thead>
          <tr>
            <th>Action</th>
            <th>Protocol</th>
            <th>Port</th>
            <th>Source (optional)</th>
            <th>Family</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          ${this._fwDraftRules.map((t,e)=>{const s=Qt(t.source??""),i=s??t.family??"both";return B`
              <tr>
                <td>
                  <select
                    @change=${t=>this._fwUpdateRule(e,{action:t.target.value})}
                  >
                    <option value="allow" ?selected=${"allow"===t.action}>allow</option>
                    <option value="deny" ?selected=${"deny"===t.action}>deny</option>
                  </select>
                </td>
                <td>
                  <select
                    @change=${t=>this._fwUpdateRule(e,{proto:t.target.value})}
                  >
                    <option value="tcp" ?selected=${"tcp"===t.proto}>tcp</option>
                    <option value="udp" ?selected=${"udp"===t.proto}>udp</option>
                  </select>
                </td>
                <td>
                  <input
                    type="number"
                    min="1"
                    max="65535"
                    .value=${t.port?String(t.port):""}
                    style="width:90px;"
                    @input=${t=>this._fwUpdateRule(e,{port:parseInt(t.target.value,10)||0})}
                  />
                </td>
                <td>
                  <input
                    type="text"
                    placeholder="e.g. 192.168.10.0/24 or fd00::/8"
                    .value=${t.source??""}
                    style="width:170px;"
                    @input=${t=>{const s=t.target.value,i=Qt(s);this._fwUpdateRule(e,{source:s,family:i??"both"})}}
                  />
                </td>
                <td>
                  <select
                    ?disabled=${null!==s}
                    title=${null!==s?"Locked: the source address pins this rule to its own address family.":"IPv4+IPv6 writes the rule into both tables; pick one family to scope it."}
                    @change=${t=>this._fwUpdateRule(e,{family:t.target.value})}
                  >
                    <option value="both" ?selected=${"both"===i}>IPv4+IPv6</option>
                    <option value="4" ?selected=${"4"===i}>IPv4</option>
                    <option value="6" ?selected=${"6"===i}>IPv6</option>
                  </select>
                </td>
                <td><button class="ha-btn danger" @click=${()=>this._fwRemoveRule(e)}>Remove</button></td>
              </tr>
            `})}
        </tbody>
      </table>
      <div class="toolbar" style="margin-top:8px;">
        <button class="ha-btn" @click=${this._fwAddRule}>+ Add rule</button>
      </div>

      <label style="display:flex;align-items:flex-start;gap:8px;font-size:12.5px;margin-top:12px;cursor:pointer;">
        <input
          type="checkbox"
          style="margin-top:2px;"
          .checked=${this._fwBackupAck}
          @change=${t=>this._fwBackupAck=t.target.checked}
        />
        <span>
          I understand the current ruleset will be backed up before this change is
          applied, and that an unconfirmed change reverts to that backup automatically
          once the test window closes.
        </span>
      </label>

      <div class="toolbar" style="margin-top:12px;">
        <button class="ha-btn" ?disabled=${!e||this._fwSubmitting} @click=${this._onProposeTest}>
          Test
        </button>
      </div>
      ${t?B`<p class="muted" style="font-size:12px;margin:6px 0 0;">${t}</p>`:W}
    `}};te.styles=Ft,te.MISCONFIG_SORT={check:t=>t.check,severity:t=>Kt(String(t.severity)),summary:t=>t.summary},te.COVERAGE_SORT={domain:t=>t.domain,files:t=>t.cov.scanned_files,oversize:t=>t.cov.skipped_oversize,over_cap:t=>t.cov.skipped_over_cap,parse_failures:t=>t.cov.parse_failures,scanned_at:t=>t.cov.scanned_at},te.SCANNER_SORT={domain:t=>t.domain,pattern:t=>t.pattern,location:t=>`${t.file}:${t.line}`,confidence:t=>Gt(Zt,t.confidence),cwe:t=>t.cwe},te.VULN_SORT={cve:t=>t.cve_id,cvss:t=>{if(null==t.cvss)return null;const e=Number(t.cvss);return Number.isNaN(e)?null:e},confidence:t=>Gt(Jt,t.confidence)},te.PORT_SORT={port:t=>t.port,proto:t=>t.proto,interface:t=>t.interface},te.FW_RULE_SORT={action:t=>t.action,proto:t=>t.proto,port:t=>t.port,source:t=>t.source??"any",family:t=>Yt(t.family)},t([ut()],te.prototype,"_scannerFindings",void 0),t([ut()],te.prototype,"_coverage",void 0),t([ut()],te.prototype,"_vulnFindings",void 0),t([ut()],te.prototype,"_misconfigFindings",void 0),t([ut()],te.prototype,"_probe",void 0),t([ut()],te.prototype,"_loading",void 0),t([ut()],te.prototype,"_error",void 0),t([ut()],te.prototype,"_scanning",void 0),t([ut()],te.prototype,"_scanError",void 0),t([ut()],te.prototype,"_exportNotice",void 0),t([ut()],te.prototype,"_firewall",void 0),t([ut()],te.prototype,"_fwDraftRules",void 0),t([ut()],te.prototype,"_fwBackupAck",void 0),t([ut()],te.prototype,"_fwSubmitting",void 0),t([ut()],te.prototype,"_fwError",void 0),t([ut()],te.prototype,"_isOwner",void 0),t([ut()],te.prototype,"_misconfigSort",void 0),t([ut()],te.prototype,"_scannerSort",void 0),t([ut()],te.prototype,"_vulnSort",void 0),t([ut()],te.prototype,"_portSort",void 0),t([ut()],te.prototype,"_fwRulesSort",void 0),t([ut()],te.prototype,"_coverageSort",void 0),te=jt=t([dt("ha-soc-scanner-view")],te);function ee(t,e,s){t.dispatchEvent(new CustomEvent("ha-soc-navigate",{detail:s?{tab:e,clientFilter:s}:{tab:e},bubbles:!0,composed:!0}))}function se(t){window.history.pushState(null,"",t),window.dispatchEvent(new CustomEvent("location-changed",{bubbles:!0,composed:!0}))}function ie(t){return`/config/devices/dashboard?historyBack=1&config_entry=${t}`}var ae;const re={lock:"Locks",siren:"Sirens",valve:"Valves"},oe=[{key:"available",label:"Available"},{key:"partial",label:"Partial"},{key:"unavailable",label:"Unavailable"},{key:"disabled",label:"Disabled"},{key:"no_entities",label:"No Entities"}],ne=["critical","high","medium","low"],le={failing:"Failing",credential:"Credential issue",communication:"Communication issue",collection:"Collection issue",errors:"Logging errors",debug_logging:"Debug logging enabled",disabled:"Disabled"},de={failing:{label:"Unavailable",colorVar:"var(--status-critical)"},credential:{label:"Unavailable",colorVar:"var(--status-critical)"},communication:{label:"Unavailable",colorVar:"var(--status-critical)"},collection:{label:"Unavailable",colorVar:"var(--status-critical)"},errors:{label:"Warning",colorVar:"var(--status-warning)"},debug_logging:{label:"Warning",colorVar:"var(--status-warning)"},disabled:{label:"Disabled",colorVar:"var(--cat-other)"}},ce=Object.fromEntries(Object.keys(le).map((t,e)=>[t,e])),pe=[10,20,50,100,"all"],he=[10,20,50,100,"all"];let ue=ae=class extends Ot{constructor(){super(...arguments),this._summary=null,this._deviceOverview=null,this._integrationOverview=null,this._peripherals=null,this._security=null,this._detections=[],this._risk={},this._users=[],this._loading=!0,this._error=null,this._deviceSearch="",this._deviceStatusFilter=null,this._deviceSort={key:"risk_score",dir:-1},this._devicePageSize=10,this._integrationSearch="",this._integrationSort=null,this._integrationPageSize=10,this._detectionSort=null}get viewId(){return"dashboard"}connectedCallback(){super.connectedCallback(),this._load()}updated(){this.classList.toggle("dark",!!this.hass?.themes?.darkMode)}async _load(){this._loading=!0,this._error=null;try{const[e,s,i,a,r,o,n,l]=await Promise.all([(t=this.hass,gt(t,{type:"ha_soc/dashboard/summary"})),kt(this.hass),St(this.hass),zt(this.hass),Rt(this.hass),mt(this.hass),vt(this.hass),_t(this.hass)]);this._summary=e,this._deviceOverview=s,this._integrationOverview=i,this._peripherals=a,this._security=r,this._detections=o,this._risk=n,this._users=l}catch(t){this._error=t?.message??String(t)}finally{this._loading=!1}var t}async _onAck(t){await yt(this.hass,t,"ack"),await this._load()}async _onResolve(t){await yt(this.hass,t,"resolved"),await this._load()}_nameFor(t){return t?this._users.find(e=>e.id===t)?.name??t:"unknown"}_goto(t){ee(this,t)}_onStatusTileClick(t){this._deviceStatusFilter=this._deviceStatusFilter===t?null:t,this.renderRoot.querySelector("#devices-card")?.scrollIntoView({behavior:"smooth",block:"start"})}_sortedFilteredDevices(){const t=this._deviceOverview?.devices??[],e=this._deviceSearch.trim().toLowerCase(),s=t.filter(t=>(!this._deviceStatusFilter||t.status===this._deviceStatusFilter)&&(!e||(t.name.toLowerCase().includes(e)||t.vendor.toLowerCase().includes(e)||t.os.toLowerCase().includes(e))));return Dt(s,this._deviceSort,ae.DEVICE_SORT)}_filteredIntegrations(){const t=this._integrationOverview?.integrations??[],e=this._integrationSearch.trim().toLowerCase();return Dt(e?t.filter(t=>t.title.toLowerCase().includes(e)||t.domain.toLowerCase().includes(e)):t,this._integrationSort,ae.INTEGRATION_SORT)}_renderPostureCard(){const t=this._summary?.posture,e=this._summary,s=this._deviceOverview;if(!t||!e||!s)return W;const i=(t.missing_terms??[]).map(t=>ae.POSTURE_TERM_LABELS[t]??t),a=this._detections.filter(t=>"open"===t.status).length,r=s.devices.reduce((t,e)=>t+e.severity_counts.critical,0),o=s.status_counts.unavailable??0,n=e.mfa_counts.disabled??0,l=t.score>=85?"good":t.score>=70?"warning":"critical";return B`
      <h2 class="section-title">Security command overview</h2>
      <p class="section-subtitle">The conditions most likely to require action, with direct paths to investigate them.</p>
      <div class="command-grid">
        <div class="card posture-card ${l}">
          <div>
            <div class="posture-kicker">Overall posture</div>
            <div class="posture-main">
              <div class="posture-grade">${t.grade}</div>
              <div>
                <div class="posture-score">${t.score} / 100</div>
                ${t.provisional?B`<span class="tag cosmetic" title="Waiting on: ${i.join(", ")}">provisional</span>`:B`<span class="tag enforced">fully calculated</span>`}
              </div>
            </div>
          </div>
          <div class="score-track" aria-label="Posture score ${t.score} out of 100">
            <div class="score-fill" style="width:${Math.max(0,Math.min(100,t.score))}%"></div>
          </div>
        </div>
        <div class="priority-grid">
          <button class="priority-item" type="button" @click=${()=>this._goto("audit")}>
            <span class="metric-label">Open detections</span>
            <span class="priority-value ${a?"critical":""}">${a}</span>
            <span class="priority-help">Review active security signals</span>
          </button>
          <button class="priority-item" type="button" @click=${()=>this._goto("scanner")}>
            <span class="metric-label">Critical CVEs</span>
            <span class="priority-value ${r?"critical":""}">${r.toLocaleString()}</span>
            <span class="priority-help">Across inventoried devices</span>
          </button>
          <button class="priority-item" type="button" @click=${()=>this._onStatusTileClick("unavailable")}>
            <span class="metric-label">Unavailable devices</span>
            <span class="priority-value ${o?"warning":""}">${o}</span>
            <span class="priority-help">Filter the investigation queue</span>
          </button>
          <button class="priority-item" type="button" @click=${()=>this._goto("users")}>
            <span class="metric-label">Accounts without MFA</span>
            <span class="priority-value ${n?"warning":""}">${n}</span>
            <span class="priority-help">Close identity protection gaps</span>
          </button>
        </div>
      </div>
    `}_statusDotColor(t){switch(t){case"unavailable":return"var(--status-critical)";case"partial":return"var(--status-warning)";case"disabled":return"var(--cat-other)";case"no_entities":return"var(--primary-color)";default:return"var(--status-good)"}}render(){if(this._loading)return B`<div class="empty">Loading dashboard…</div>`;if(this._error||!this._summary||!this._deviceOverview||!this._integrationOverview)return B`
        <div class="card" style="border:1px solid var(--error-color,#db4437);">
          <h3>Could not load the dashboard</h3>
          <p style="font-size:13px;">
            ${this._error??"The server returned an incomplete dashboard payload."}
          </p>
          <button class="ha-btn" @click=${()=>this._load()}>Retry</button>
        </div>
      `;const t=this._summary,e=this._deviceOverview,s=this._integrationOverview,i=Dt(this._detections.filter(t=>"open"===t.status),this._detectionSort,{time:t=>t.last_seen,rule:t=>t.title,severity:t=>{const e=ne.indexOf(t.severity);return-1===e?ne.length:e},user:t=>this._nameFor(t.user_id)}),a=t=>{this._detectionSort=t},r=e.devices.reduce((t,e)=>(t.critical+=e.severity_counts.critical,t.high+=e.severity_counts.high,t.medium+=e.severity_counts.medium,t.low+=e.severity_counts.low,t),{critical:0,high:0,medium:0,low:0}),o=r.critical+r.high+r.medium+r.low,n=[{key:"critical",label:"Critical",color:"var(--status-critical)",value:r.critical},{key:"high",label:"High",color:"var(--status-serious)",value:r.high},{key:"medium",label:"Medium",color:"var(--status-warning)",value:r.medium},{key:"low",label:"Low",color:"var(--status-good)",value:r.low}],l=t.entity_state_counts??{unavailable:0,unknown:0},d=l.unavailable+l.unknown,c=this._sortedFilteredDevices(),p="all"===this._devicePageSize?c:c.slice(0,this._devicePageSize),h=t=>{this._deviceSort=t},u=t=>{this._integrationSort=t},g=this._filteredIntegrations(),_="all"===this._integrationPageSize?g:g.slice(0,this._integrationPageSize),v=[{key:"critical",color:"var(--status-critical)",value:t.detection_severity_counts.critical??0},{key:"high",color:"var(--status-serious)",value:t.detection_severity_counts.high??0},{key:"medium",color:"var(--status-warning)",value:t.detection_severity_counts.medium??0},{key:"low",color:"var(--status-good)",value:t.detection_severity_counts.low??0}],m=[{id:"posture_security",title:"Posture & Security",hideable:!1,render:()=>B`${this._renderPostureCard()} ${this._renderSecurityCard()}`},{id:"device_vuln_overview",title:"Device & Vulnerability Overview",render:()=>B`
      <h2 class="section-title">Exposure at a glance</h2>
      <p class="section-subtitle">Availability, vulnerability concentration, and entity reliability without the chart clutter.</p>
      <div class="summary-grid">
        <div class="card device-status-card">
          <div class="card-head">
            <div>
              <h3>Device availability</h3>
              <div class="metric-context">${e.devices.length.toLocaleString()} inventoried devices</div>
            </div>
          </div>
          <div class="status-tiles">
            ${oe.map(t=>B`
                <div
                  class="status-tile clickable ${t.key} ${this._deviceStatusFilter===t.key?"active":""}"
                  title="Filter the devices table below"
                  @click=${()=>this._onStatusTileClick(t.key)}
                >
                  <div class="label">${t.label}</div>
                  <div class="value">${e.status_counts[t.key]??0}</div>
                </div>
              `)}
          </div>
        </div>

        <div class="card clickable" @click=${()=>this._goto("scanner")} title="View vulnerability findings">
          <div class="card-head">
            <div>
              <h3>Vulnerability exposure</h3>
              <div class="metric-context">Weighted risk score ${e.combined_risk_score.toFixed(1)} / 10</div>
            </div>
            <div class="metric-number">${o.toLocaleString()}</div>
          </div>
          <div class="severity-track" aria-label="Vulnerability findings by severity">
            ${n.map(t=>B`<span style="width:${o?t.value/o*100:0}%;background:${t.color}"></span>`)}
          </div>
          <div class="compact-legend">
            ${n.map(t=>B`
                <div class="item">
                  <span class="swatch" style="background:${t.color}"></span>${t.label}
                  <strong>${t.value.toLocaleString()}</strong>
                </div>
              `)}
          </div>
        </div>

        <div class="card clickable" @click=${()=>this._goto("entity_remap")} title="Fix broken entity references">
          <div class="card-head">
            <div>
              <h3>Entity reliability</h3>
              <div class="metric-context">Failed and unknown entity states</div>
            </div>
            <div class="metric-number">${d.toLocaleString()}</div>
          </div>
          <div class="identity-grid" style="grid-template-columns:repeat(2,minmax(0,1fr));">
            <div class="identity-stat">
              <div class="metric-label">Unavailable</div>
              <div class="value" style="color:var(--status-critical)">${l.unavailable.toLocaleString()}</div>
            </div>
            <div class="identity-stat">
              <div class="metric-label">Unknown</div>
              <div class="value" style="color:var(--status-warning)">${l.unknown.toLocaleString()}</div>
            </div>
          </div>
        </div>
      </div>
        `},{id:"users_detections",title:"Users & Detections",render:()=>B`
      <h2 class="section-title">Identity and active detections</h2>
      <p class="section-subtitle">Account protection and the security signals that need review.</p>
      <div class="row2">
        <div class="card clickable" @click=${()=>this._goto("users")} title="View users">
          <div class="card-head">
            <div>
              <h3>Identity protection</h3>
              <div class="metric-context">MFA adoption across eligible accounts</div>
            </div>
            <div class="metric-number">
              ${t.mfa_counts.enabled+t.mfa_counts.disabled>0?`${Math.round(t.mfa_counts.enabled/(t.mfa_counts.enabled+t.mfa_counts.disabled)*100)}%`:"—"}
            </div>
          </div>
          <div class="mfa-track" aria-label="MFA adoption">
            <div
              class="mfa-fill"
              style="width:${t.mfa_counts.enabled+t.mfa_counts.disabled>0?t.mfa_counts.enabled/(t.mfa_counts.enabled+t.mfa_counts.disabled)*100:0}%"
            ></div>
          </div>
          <div class="identity-grid" style="margin-top:14px;">
            <div class="identity-stat">
              <div class="metric-label">Users</div>
              <div class="value">${t.total_users_count}</div>
            </div>
            <div class="identity-stat">
              <div class="metric-label">High / critical risk</div>
              <div class="value">${(t.risk_band_counts.high??0)+(t.risk_band_counts.critical??0)}</div>
            </div>
            <div class="identity-stat">
              <div class="metric-label">No MFA</div>
              <div class="value" style="color:var(--status-serious)">${t.mfa_counts.disabled}</div>
            </div>
          </div>
        </div>

        <div class="card clickable" @click=${()=>this._goto("audit")} title="View audit / detections">
          <div class="card-head">
            <div>
              <h3>Detection coverage</h3>
              <div class="metric-context">${i.length} currently open</div>
            </div>
            <div class="metric-number">${this._detections.length}</div>
          </div>
          <div class="severity-track" aria-label="Detections by severity">
            ${v.map(t=>B`<span style="width:${this._detections.length?t.value/this._detections.length*100:0}%;background:${t.color}"></span>`)}
          </div>
          <div class="compact-legend">
            ${v.map(t=>B`
                <div class="item">
                  <span class="swatch" style="background:${t.color}"></span>${t.key}
                  <strong>${t.value}</strong>
                </div>
              `)}
          </div>
        </div>
        </div>
      </div>

      <div class="card">
        <div class="card-head">
          <div>
            <h3>Active investigation queue</h3>
            <div class="metric-context">Open detections, newest activity first</div>
          </div>
        </div>
        ${i.length?B`
              <table>
                <thead>
                  <tr>
                    ${Ut("Time","time",this._detectionSort,a)}
                    ${Ut("Rule","rule",this._detectionSort,a)}
                    ${Ut("Severity","severity",this._detectionSort,a)}
                    ${Ut("User","user",this._detectionSort,a)}
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  ${i.map(t=>B`
                      <tr>
                        <td>${new Date(t.last_seen).toLocaleString()}</td>
                        <td>${t.title}</td>
                        <td><span class="pill ${t.severity}"><span class="dot"></span>${t.severity}</span></td>
                        <td>${this._nameFor(t.user_id)}</td>
                        <td>
                          <button class="ha-btn" @click=${()=>this._onAck(t.id)}>Ack</button>
                          <button class="ha-btn" @click=${()=>this._onResolve(t.id)}>Resolve</button>
                        </td>
                      </tr>
                    `)}
                </tbody>
              </table>
            `:B`<div class="empty">No open detections. The active queue is clear.</div>`}
      </div>
        `},{id:"devices_integrations",title:"Devices & Integrations",render:()=>B`
      <h2 class="section-title">Investigation queues</h2>
      <p class="section-subtitle">The highest-risk devices and integration failures, sorted for triage.</p>
      <div class="row2">
        <div class="card" id="devices-card">
          <div class="card-head">
            <div>
              <h3>Highest-risk devices</h3>
              <div class="metric-context">Select a row to open the Home Assistant device record</div>
            </div>
          </div>
          ${this._deviceStatusFilter?B`
                <div class="filter-chip" @click=${()=>this._deviceStatusFilter=null}>
                  ${oe.find(t=>t.key===this._deviceStatusFilter)?.label} ✕
                </div>
              `:W}
          <div class="devices-toolbar">
            <input
              type="text"
              placeholder="Search devices…"
              .value=${this._deviceSearch}
              @input=${t=>this._deviceSearch=t.target.value}
            />
          </div>
          ${0===c.length?B`<div class="empty">No devices found.</div>`:B`
                <div style="overflow-x:auto;">
                  <table>
                    <thead>
                      <tr>
                        ${Ut("Health","status",this._deviceSort,h)}
                        ${Ut("Device","name",this._deviceSort,h)}
                        ${Ut("Vendor","vendor",this._deviceSort,h)}
                        ${Ut("Risk Score","risk_score",this._deviceSort,h,{numeric:!0})}
                        ${Ut("Total","total_findings",this._deviceSort,h,{numeric:!0})}
                        ${Ut("Severity","severity",this._deviceSort,h)}
                      </tr>
                    </thead>
                    <tbody>
                      ${p.map(t=>B`
                          <tr
                            class="clickable"
                            title="Open in Home Assistant's Devices page"
                            @click=${()=>se(`/config/devices/device/${t.device_id}`)}
                          >
                            <td>
                              <span
                                class="health-dot"
                                title=${t.status.replace("_"," ")}
                                aria-label=${t.status.replace("_"," ")}
                                style="background:${this._statusDotColor(t.status)}"
                              ></span>
                            </td>
                            <td>${t.name}</td>
                            <td class="muted">${t.vendor}</td>
                            <td class="num">${t.risk_score.toFixed(1)}</td>
                            <td class="num">${t.total_findings}</td>
                            <td>
                              <span class="sev-cell">
                                ${ne.map(e=>B`
                                    <span>
                                      <span
                                        class="sev-dot"
                                        style="background:${"critical"===e?"var(--status-critical)":"high"===e?"var(--status-serious)":"medium"===e?"var(--status-warning)":"var(--status-good)"}"
                                      ></span
                                      >${t.severity_counts[e]}
                                    </span>
                                  `)}
                              </span>
                            </td>
                          </tr>
                        `)}
                    </tbody>
                  </table>
                </div>
                <div class="devices-footer">
                  <span
                    >Showing ${p.length} of ${c.length} device${1===c.length?"":"s"}</span
                  >
                  <select
                    .value=${String(this._devicePageSize)}
                    @change=${t=>{const e=t.target.value;this._devicePageSize="all"===e?"all":Number(e)}}
                  >
                    ${pe.map(t=>B`
                        <option value=${String(t)} ?selected=${t===this._devicePageSize}>
                          ${"all"===t?"Show all":`Show ${t}`}
                        </option>
                      `)}
                  </select>
                </div>
              `}
        </div>

        <div class="card">
          <div class="card-head">
            <div>
              <h3>Integration issues</h3>
              <div class="metric-context">Setup, credential, communication, and logging health</div>
            </div>
          </div>
          ${0===s.integrations.length?B`<div class="empty">No integration issues detected.</div>`:B`
                <div class="devices-toolbar">
                  <input
                    type="text"
                    placeholder="Search integrations…"
                    .value=${this._integrationSearch}
                    @input=${t=>this._integrationSearch=t.target.value}
                  />
                </div>
                ${0===g.length?B`<div class="empty">No integration matches "${this._integrationSearch}".</div>`:B`
                      <div style="overflow-x:auto;">
                        <table>
                          <thead>
                            <tr>
                              ${Ut("Integration","title",this._integrationSort,u)}
                              ${Ut("Severity","severity",this._integrationSort,u)}
                            </tr>
                          </thead>
                          <tbody>
                            ${_.map(t=>{const e=de[t.issue_category];return B`
                                <tr
                                  class="clickable"
                                  title="${t.title} — ${le[t.issue_category]}. Open in Home Assistant's Devices page"
                                  @click=${()=>se(ie(t.entry_id))}
                                >
                                  <td>${t.title}</td>
                                  <td>
                                    <span class="sev-cell">
                                      <span class="sev-dot" style="background:${e.colorVar}"></span>
                                      ${e.label}
                                      ${t.error_count_24h?B`<span class="num">${t.error_count_24h} error${1===t.error_count_24h?"":"s"}</span>`:W}
                                    </span>
                                  </td>
                                </tr>
                              `})}
                          </tbody>
                        </table>
                      </div>
                      <div class="devices-footer">
                        <span
                          >Showing ${_.length} of ${g.length} integration${1===g.length?"":"s"}</span
                        >
                        <select
                          .value=${String(this._integrationPageSize)}
                          @change=${t=>{const e=t.target.value;this._integrationPageSize="all"===e?"all":Number(e)}}
                        >
                          ${he.map(t=>B`
                              <option value=${String(t)} ?selected=${t===this._integrationPageSize}>
                                ${"all"===t?"Show all":`Show ${t}`}
                              </option>
                            `)}
                        </select>
                      </div>
                    `}
              `}
        </div>
      </div>
        `}];return this._renderSections(m)}_renderSecurityCard(){const t=this._security;if(!t)return W;const e={};for(const s of t.entities)(e[s.domain]??=[]).push(s);return B`
      <div class="card">
        <div class="card-head">
          <div>
            <h3>Security-source health</h3>
            <div class="metric-context">Locks, sirens, valves, and local peripherals</div>
          </div>
          ${t.problem_count||t.low_battery_count?B`<span class="tag" style="background:rgba(219,68,55,0.15);color:var(--error-color,#db4437);">
                ${t.problem_count} problem${1===t.problem_count?"":"s"} · ${t.low_battery_count} low battery
              </span>`:B`<span class="tag enforced">all clear</span>`}
        </div>
        <div class="security-health-grid">
          ${Object.entries(re).filter(([e])=>t.sources_enabled[e]??!0).map(([t,s])=>{const i=e[t]??[],a=i.filter(t=>t.problem),r=a.length,o=i.filter(t=>t.low_battery).length,n=a.slice(0,8).map(t=>`${t.entity_id}: ${t.reason??t.state??"problem"}`);r>8&&n.push(`and ${r-8} more`);const l=i.length?[`View ${s.toLowerCase()} in Home Assistant's Devices page`,...n].join("\n"):"";return B`
                <div
                  class="security-source-tile ${i.length?"clickable":""}"
                  title=${l}
                  @click=${()=>i.length&&se(function(t){return`/config/devices/dashboard?historyBack=1&domain=${t}`}(t))}
                >
                  <div class="label">${s}</div>
                  <div class="value" style="color:${r?"var(--error-color,#db4437)":"inherit"}">
                    ${r}
                  </div>
                  <div class="sub">
                    ${i.length} total${o?`, ${o} low battery`:""}
                  </div>
                </div>
              `})}
          ${this._renderPeripheralsTile()}
        </div>
      </div>
    `}_renderPeripheralsTile(){const t=this._peripherals;return t&&t.available?B`
      <div
        class="security-source-tile clickable"
        title="View Local Peripherals"
        @click=${()=>this._goto("peripherals")}
      >
        <div class="label">Local Peripherals</div>
        <div class="value" style="color:${t.unassigned_count?"var(--status-warning)":"inherit"}">
          ${t.total_count?t.unassigned_count:0}
        </div>
        <div class="sub">
          ${t.total_count?`${t.total_count} total`:"no USB serial devices detected"}
        </div>
      </div>
    `:W}};var ge;ue.styles=[Ft,o`
      h2.section-title {
        font-size: 18px;
        letter-spacing: -0.01em;
        color: var(--primary-text-color);
        margin: 30px 0 4px;
        font-weight: 650;
      }
      h2.section-title:first-child {
        margin-top: 0;
      }

      .row3 {
        display: grid;
        grid-template-columns: minmax(320px, 1.35fr) repeat(3, minmax(190px, 1fr));
        gap: 12px;
        margin-bottom: 16px;
      }
      .row2 {
        display: grid;
        grid-template-columns: minmax(0, 1.65fr) minmax(300px, 1fr);
        gap: 12px;
        margin-bottom: 16px;
      }
      .donuts-row {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 12px;
        margin-bottom: 16px;
      }
      @media (max-width: 900px) {
        .row3,
        .row2,
        .donuts-row {
          grid-template-columns: 1fr;
        }
      }

      .clickable {
        cursor: pointer;
        transition: transform 0.08s ease, box-shadow 0.08s ease;
      }
      .clickable:hover {
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.12);
        transform: translateY(-1px);
      }

      .section-subtitle {
        color: var(--secondary-text-color);
        font-size: 13px;
        line-height: 1.45;
        margin: 0 0 14px;
      }
      .command-grid {
        display: grid;
        grid-template-columns: minmax(280px, 0.85fr) minmax(0, 2fr);
        gap: 12px;
        margin-bottom: 12px;
      }
      .posture-card {
        margin: 0;
        border-left: 5px solid var(--status-critical);
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        min-height: 142px;
      }
      .posture-card.good {
        border-left-color: var(--status-good);
      }
      .posture-card.warning {
        border-left-color: var(--status-warning);
      }
      .posture-kicker,
      .metric-label {
        color: var(--secondary-text-color);
        font-size: 11px;
        font-weight: 650;
        letter-spacing: 0.055em;
        text-transform: uppercase;
      }
      .posture-main {
        display: flex;
        align-items: baseline;
        gap: 12px;
        margin: 8px 0 14px;
      }
      .posture-grade {
        font-size: 52px;
        font-weight: 750;
        letter-spacing: -0.045em;
        line-height: 0.9;
      }
      .posture-score {
        font-size: 18px;
        font-weight: 650;
      }
      .score-track,
      .severity-track,
      .mfa-track {
        height: 7px;
        border-radius: 999px;
        overflow: hidden;
        background: rgba(var(--rgb-primary-text-color, 0, 0, 0), 0.09);
      }
      .score-fill,
      .mfa-fill {
        height: 100%;
        border-radius: inherit;
        background: var(--primary-color);
      }
      .priority-grid {
        display: grid;
        grid-template-columns: repeat(4, minmax(120px, 1fr));
        gap: 10px;
      }
      button.priority-item {
        appearance: none;
        font: inherit;
        color: var(--primary-text-color);
        text-align: left;
        background: var(--card-background-color, #fff);
        border: 1px solid var(--divider-color);
        border-radius: var(--ha-card-border-radius, 12px);
        padding: 15px;
        cursor: pointer;
        min-height: 142px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        transition: border-color 0.12s ease, transform 0.12s ease;
      }
      button.priority-item:hover,
      button.priority-item:focus-visible {
        border-color: var(--primary-color);
        transform: translateY(-1px);
        outline: none;
      }
      .priority-value {
        font-size: 31px;
        font-weight: 720;
        line-height: 1;
        margin: 10px 0 5px;
        font-variant-numeric: tabular-nums;
      }
      .priority-value.critical {
        color: var(--status-critical);
      }
      .priority-value.warning {
        color: var(--status-serious);
      }
      .priority-help {
        color: var(--secondary-text-color);
        font-size: 11.5px;
        line-height: 1.35;
      }
      .summary-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 12px;
        margin-bottom: 16px;
      }
      .summary-grid > .card {
        margin: 0;
      }
      .card-head {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 12px;
        margin-bottom: 14px;
      }
      .card-head h3 {
        margin: 0;
      }
      .metric-number {
        font-size: 34px;
        font-weight: 720;
        line-height: 1;
        letter-spacing: -0.025em;
        font-variant-numeric: tabular-nums;
      }
      .metric-context {
        color: var(--secondary-text-color);
        font-size: 12px;
        margin-top: 5px;
      }
      .severity-track {
        display: flex;
        margin: 16px 0 12px;
      }
      .severity-track > span {
        min-width: 2px;
      }
      .compact-legend {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 7px 12px;
        font-size: 12px;
      }
      .compact-legend .item {
        display: flex;
        align-items: center;
        gap: 6px;
      }
      .compact-legend .item strong {
        margin-left: auto;
        font-variant-numeric: tabular-nums;
      }
      .compact-legend .swatch {
        width: 8px;
        height: 8px;
        border-radius: 2px;
      }
      .identity-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 10px;
      }
      .identity-stat {
        border: 1px solid var(--divider-color);
        border-radius: 10px;
        padding: 12px;
      }
      .identity-stat .value {
        font-size: 24px;
        font-weight: 700;
        margin-top: 5px;
      }

      /* -- Status tiles -------------------------------------------------- */
      /* Stretches to fill whatever height row3's tallest sibling card
         (the donut / gauge cards) ends up at, rather than sizing to its
         own short content and leaving dead space below. */
      .device-status-card {
        display: flex;
        flex-direction: column;
      }
      .status-tiles {
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 8px;
        flex: 1;
      }
      .status-tile {
        border-radius: 10px;
        padding: 10px 6px;
        text-align: center;
        background: var(--card-background-color, #fff);
        border: 1px solid var(--divider-color);
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 6px;
      }
      .status-tile.active {
        outline: 2px solid var(--primary-color);
        outline-offset: -2px;
      }
      .status-tile .label {
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        opacity: 0.85;
      }
      .status-tile .value {
        font-size: 26px;
        font-weight: 700;
        line-height: 1.3;
      }
      .status-tile.partial {
        border-top: 3px solid var(--status-warning);
      }
      .status-tile.unavailable {
        border-top: 3px solid var(--status-critical);
      }
      .status-tile.unavailable .value {
        color: var(--status-critical);
      }
      .status-tile.disabled {
        border-top: 3px solid var(--cat-other);
      }
      .status-tile.no_entities {
        border-top: 3px solid var(--primary-color);
      }

      .filter-chip {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-size: 12px;
        background: var(--primary-color);
        color: #fff;
        padding: 4px 10px;
        border-radius: 100px;
        cursor: pointer;
        margin-bottom: 10px;
      }

      /* -- All Devices table --------------------------------------------------- */
      .devices-toolbar {
        display: flex;
        gap: 8px;
        margin-bottom: 10px;
      }
      .devices-toolbar input {
        flex: 1;
        font: inherit;
        font-size: 13px;
        padding: 7px 10px;
        border-radius: 8px;
        border: 1px solid var(--divider-color);
        background: var(--card-background-color, #fff);
        color: var(--primary-text-color);
      }
      .health-dot {
        display: inline-block;
        width: 9px;
        height: 9px;
        border-radius: 50%;
      }
      .sev-cell {
        display: inline-flex;
        gap: 8px;
        font-variant-numeric: tabular-nums;
        font-size: 11.5px;
      }
      .sev-cell span {
        display: inline-flex;
        align-items: center;
        gap: 3px;
      }
      .sev-dot {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        display: inline-block;
      }

      /* -- All Devices pagination ------------------------------------------ */
      .devices-footer {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-top: 10px;
        font-size: 12.5px;
        color: var(--secondary-text-color);
      }
      .devices-footer select {
        margin-left: auto;
      }

      /* -- Security Integrations Health card --------------------------------- */
      .security-health-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 8px;
        margin-top: 8px;
      }
      .security-source-tile {
        border: 1px solid var(--divider-color);
        border-radius: 8px;
        padding: 9px 11px;
      }
      .security-source-tile .label {
        font-size: 12px;
        color: var(--secondary-text-color);
        margin-bottom: 4px;
      }
      .security-source-tile .value {
        font-size: 18px;
        font-weight: 700;
      }
      .security-source-tile .sub {
        font-size: 11px;
        color: var(--secondary-text-color);
        margin-top: 2px;
      }
      @media (max-width: 1100px) {
        .command-grid {
          grid-template-columns: 1fr;
        }
        .priority-grid {
          grid-template-columns: repeat(2, minmax(0, 1fr));
        }
        button.priority-item {
          min-height: 116px;
        }
      }
      @media (max-width: 900px) {
        .summary-grid,
        .identity-grid {
          grid-template-columns: 1fr;
        }
      }
      @media (max-width: 560px) {
        .priority-grid {
          grid-template-columns: 1fr 1fr;
        }
        .status-tiles {
          grid-template-columns: repeat(2, 1fr);
        }
      }
    `],ue.DEVICE_SORT={status:t=>oe.findIndex(e=>e.key===t.status),name:t=>t.name,vendor:t=>t.vendor,risk_score:t=>t.risk_score,total_findings:t=>t.total_findings,severity:t=>1e9*t.severity_counts.critical+1e6*t.severity_counts.high+1e3*t.severity_counts.medium+t.severity_counts.low},ue.INTEGRATION_SORT={title:t=>t.title,severity:t=>ce[t.issue_category]},ue.POSTURE_TERM_LABELS={p_user:"user risk",p_vuln:"device vulnerabilities",p_misconfig:"misconfigurations",p_integration:"integration health",p_detection:"detections"},t([ut()],ue.prototype,"_summary",void 0),t([ut()],ue.prototype,"_deviceOverview",void 0),t([ut()],ue.prototype,"_integrationOverview",void 0),t([ut()],ue.prototype,"_peripherals",void 0),t([ut()],ue.prototype,"_security",void 0),t([ut()],ue.prototype,"_detections",void 0),t([ut()],ue.prototype,"_risk",void 0),t([ut()],ue.prototype,"_users",void 0),t([ut()],ue.prototype,"_loading",void 0),t([ut()],ue.prototype,"_error",void 0),t([ut()],ue.prototype,"_deviceSearch",void 0),t([ut()],ue.prototype,"_deviceStatusFilter",void 0),t([ut()],ue.prototype,"_deviceSort",void 0),t([ut()],ue.prototype,"_devicePageSize",void 0),t([ut()],ue.prototype,"_integrationSearch",void 0),t([ut()],ue.prototype,"_integrationSort",void 0),t([ut()],ue.prototype,"_integrationPageSize",void 0),t([ut()],ue.prototype,"_detectionSort",void 0),ue=ae=t([dt("ha-soc-dashboard-view")],ue);const _e=[25,50,100,"all"];function ve(t){if(!t)return null;try{const e=new URL(t).protocol;return"http:"===e||"https:"===e?t:null}catch{return null}}let me=ge=class extends Ot{constructor(){super(...arguments),this.initialClientFilter=null,this._overview=null,this._loading=!0,this._error=null,this._clientSearch="",this._clientPage=0,this._clientPageSize=25,this._clientVlanFilter="",this._clientSsidFilter="",this._clientSort=null,this._deviceSearch="",this._devicePage=0,this._devicePageSize=25,this._deviceSort=null,this._protectSort=null,this._eventSort=null}get viewId(){return"network"}connectedCallback(){super.connectedCallback(),this._load()}updated(t){super.updated(t),t.has("initialClientFilter")&&this.initialClientFilter&&(this._clientSearch=this.initialClientFilter,this._clientPage=0,this.dispatchEvent(new CustomEvent("client-filter-consumed")))}async _load(){this._loading=!0,this._error=null;try{this._overview=await(t=this.hass,gt(t,{type:"ha_soc/network/overview"}))}catch(t){this._error=t instanceof Error?t.message:String(t),this._overview=null}finally{this._loading=!1}var t}_fmtBytes(t){if(null==t)return"—";if(t<1024)return`${t} B`;const e=["KB","MB","GB","TB","PB"];let s=t/1024,i=0;for(;s>=1024&&i<e.length-1;)s/=1024,i++;return`${s.toFixed(s>=100?0:1)} ${e[i]}`}_fmtRate(t){if(null==t)return"—";const e=8*t;if(e<1e3)return`${e} bps`;const s=["kbps","Mbps","Gbps"];let i=e/1e3,a=0;for(;i>=1e3&&a<s.length-1;)i/=1e3,a++;return`${i.toFixed(i>=100?0:1)} ${s[a]}`}_fmtBandwidth(t){return t?`↓ ${this._fmtBytes(t.rx_bytes)} · ↑ ${this._fmtBytes(t.tx_bytes)}`:"—"}_fmtUptime(t){if(null==t)return"—";const e=Math.floor(t/86400),s=Math.floor(t%86400/3600),i=Math.floor(t%3600/60);return e>0?`${e}d ${s}h`:s>0?`${s}h ${i}m`:`${i}m`}_fmtLastSeen(t){if(null==t)return"—";const e=Date.now()/1e3,s=Math.max(0,e-t);return s<60?"just now":s<3600?`${Math.floor(s/60)}m ago`:s<86400?`${Math.floor(s/3600)}h ago`:s<2592e3?`${Math.floor(s/86400)}d ago`:new Date(1e3*t).toLocaleDateString()}_fmtVlan(t){return null==t||""===t?"—":String(t)}_renderMatch(t){const e=t.integration_match;if(!e)return B`<span class="muted">—</span>`;const s=e.failing?"failing":e.healthy?"healthy":"other",i=e.failing?"⚠":e.healthy?"●":"○",a=`${e.domain} — config entry state: ${e.state}. Click to open in Home Assistant.`;return B`
      <span
        class="match ${s}"
        title=${a}
        @click=${()=>se(ie(e.entry_id))}
      >
        ${i} ${e.domain}${e.failing?" failing":""}
      </span>
    `}_filter(t,e){const s=e.trim().toLowerCase();return s?t.filter(t=>[t.name,t.ipv4,t.ipv6,t.mac,t.ssid,t.integration_match?.domain].filter(Boolean).some(t=>String(t).toLowerCase().includes(s))):t}_paginate(t,e,s){return"all"===s?t:t.slice(e*s,e*s+s)}render(){if(this._loading)return B`<div class="empty">Loading network…</div>`;if(this._error)return B`<div class="alert">Could not load the Network overview: ${this._error}</div>`;const t=this._overview;if(!t)return B`<div class="empty">No network data.</div>`;if(!t.configured)return B`
        <div class="card">
          <h3>UniFi Network not configured</h3>
          <p class="muted" style="font-size:13px;line-height:1.6;">
            Add a UniFi Network controller host and a local API key in
            <strong>Settings</strong> (owner only) to see status, WAN throughput,
            wireless clients, and the client / device tables here. The API key is a
            local one generated on the console under
            <em>Settings → Control Plane → Integrations</em>; nothing leaves your LAN.
          </p>
          <button class="ha-btn" @click=${()=>ee(this,"settings")}>
            Open Settings
          </button>
        </div>
        ${this._renderProtectCard(t)}
      `;if(!t.reachable)return B`
        <div class="alert">
          <strong>UniFi Network is configured but not reachable.</strong><br />
          ${t.error??"Unknown error."}
        </div>
        <button class="ha-btn" @click=${()=>this._load()}>Retry</button>
        ${this._renderProtectCard(t)}
      `;const e=[{id:"overview",title:"Status & Wireless Overview",hideable:!1,render:()=>B`${this._renderFailingBanner(t)} ${this._renderStats(t)} ${this._renderSsid(t)}`},{id:"clients",title:"Clients",render:()=>this._renderClientsTable(t)},{id:"devices",title:"Network Devices",render:()=>this._renderDevicesTable(t)},{id:"protect",title:"UniFi Protect",render:()=>this._renderProtectCard(t)}];return B`
      ${this._renderSections(e)}
      <div class="footer">
        <span>Last updated ${new Date(t.generated_at).toLocaleTimeString()}</span>
        <button class="ha-btn" style="margin-left:auto;" @click=${()=>this._load()}>
          Refresh
        </button>
      </div>
    `}_renderFailingBanner(t){return t.failing_endpoint_count?B`
      <div class="alert">
        <strong>⚠ ${t.failing_endpoint_count} Home Assistant integration${1===t.failing_endpoint_count?"":"s"} with a failing config entry ${1===t.failing_endpoint_count?"is":"are"} still present on the network.</strong>
        An integration whose device is online (a live client below) but whose config
        entry is in a setup-error/retry state is exactly the "an integration IP is
        failing" case — the device is reachable, so the fault is the integration, not
        the network. Look for the red <span class="match failing" style="cursor:default;"
        >⚠ failing</span> tags in the Integration column.
      </div>
    `:W}_renderStats(t){const e="online"===t.status,s=t.internet_connected;return B`
      <div class="stat-row">
        <div class="stat-tile">
          <div class="label">Network Status</div>
          <div class="value">
            <span class="dot ${e?"good":"bad"}"></span>${e?"Online":"Offline"}
          </div>
          <div class="sub">${t.site_id?`site ${t.site_id}`:""}</div>
        </div>
        <div class="stat-tile">
          <div class="label">Internet</div>
          <div class="value">
            <span class="dot ${!0===s?"good":!1===s?"bad":"unknown"}"></span>${!0===s?"Connected":!1===s?"Down":"Unknown"}
          </div>
          <div class="sub">${t.wan.ip?`WAN ${t.wan.ip}`:t.wan.port?t.wan.port:"—"}</div>
        </div>
        <div class="stat-tile">
          <div class="label">WAN Bandwidth</div>
          <div class="value" style="font-size:18px;">
            ↓ ${this._fmtRate(t.wan.rx_rate_bps)}
          </div>
          <div class="sub">↑ ${this._fmtRate(t.wan.tx_rate_bps)}${t.wan.port?` · ${t.wan.port}`:""}</div>
        </div>
        <div class="stat-tile">
          <div class="label">Wireless Clients</div>
          <div class="value">${t.wireless_client_count}</div>
          <div class="sub">${t.wired_client_count} wired</div>
        </div>
        <div class="stat-tile">
          <div class="label">Total Clients</div>
          <div class="value">${t.total_client_count}</div>
          <div class="sub">${t.devices.length} network devices</div>
        </div>
      </div>
    `}_selectSsid(t){this._clientSsidFilter=this._clientSsidFilter===t?"":t,this._clientPage=0,this._clientSsidFilter&&this.updateComplete.then(()=>{this.renderRoot?.querySelector("#clients-card")?.scrollIntoView({behavior:"smooth",block:"start"})})}_renderSsid(t){if(!t.clients_per_ssid.length)return W;const e=Math.max(...t.clients_per_ssid.map(t=>t.count),1);return B`
      <div class="card">
        <h3>Clients per SSID <span class="muted" style="font-weight:400;font-size:12px;">— click to filter the table</span></h3>
        <div class="ssid-list">
          ${t.clients_per_ssid.map(t=>B`
              <div
                class="ssid-row clickable ${this._clientSsidFilter===t.ssid?"active":""}"
                @click=${()=>this._selectSsid(t.ssid)}
                title="Filter Clients to ${t.ssid}"
              >
                <span class="name">${t.ssid}</span>
                <span class="bar"><span style="width:${t.count/e*100}%"></span></span>
                <span class="count">${t.count}</span>
              </div>
            `)}
        </div>
      </div>
    `}_colHeaders(){const t=this._clientSort,e=t=>{this._clientSort=t,this._clientPage=0};return B`
      <tr>
        ${Ut("Client","name",t,e)}
        ${Ut("IPv4","ipv4",t,e)}
        ${Ut("IPv6","ipv6",t,e)}
        ${Ut("MAC","mac",t,e)}
        ${Ut("VLAN","vlan",t,e,{numeric:!0})}
        ${Ut("SSID","ssid",t,e)}
        ${Ut("Uptime","uptime",t,e,{numeric:!0})}
        ${Ut("Bandwidth","bandwidth",t,e)}
        ${Ut("Last Seen","last_seen",t,e)}
        ${Ut("Integration","integration",t,e)}
      </tr>
    `}_renderRow(t,e={}){const s=t;return B`
      <tr>
        <td>
          <div style="font-weight:600;">${t.name}</div>
          ${e.model||t.wired?e.model&&s.state?B`<div class="muted" style="font-size:11px;">${s.state.toLowerCase()}</div>`:W:B`<div class="muted" style="font-size:11px;">wireless</div>`}
        </td>
        <td class="mono">${t.ipv4??"—"}</td>
        <td class="mono">${t.ipv6??"—"}</td>
        <td class="mono">${t.mac??"—"}</td>
        <td class="num">${this._fmtVlan(t.vlan)}</td>
        <td>${t.ssid??(t.wired?B`<span class="muted">wired</span>`:"—")}</td>
        ${e.model?B`<td>${s.model??"—"}</td>`:W}
        <td class="num">${this._fmtUptime(t.uptime)}</td>
        <td>${this._fmtBandwidth(t.bandwidth)}</td>
        <td>${this._fmtLastSeen(t.last_seen)}</td>
        <td>${this._renderMatch(t)}</td>
      </tr>
    `}_renderClientsTable(t){const e=Array.from(new Set(t.clients.map(t=>null==t.vlan||""===t.vlan?null:String(t.vlan)).filter(Boolean))).sort((t,e)=>Number(t)-Number(e)),s=Array.from(new Set(t.clients.map(t=>t.ssid).filter(Boolean))).sort();let i=this._filter(t.clients,this._clientSearch);this._clientVlanFilter&&(i=i.filter(t=>String(t.vlan??"")===this._clientVlanFilter)),this._clientSsidFilter&&(i=i.filter(t=>t.ssid===this._clientSsidFilter)),i=Dt(i,this._clientSort,ge.CLIENT_SORT);const a=this._paginate(i,this._clientPage,this._clientPageSize);return B`
      <div class="card" id="clients-card">
        <h3>Clients (${i.length})</h3>
        <div class="filters">
          <label
            >VLAN
            <select
              .value=${this._clientVlanFilter}
              @change=${t=>{this._clientVlanFilter=t.target.value,this._clientPage=0}}
            >
              <option value="">All</option>
              ${e.map(t=>B`<option value=${t} ?selected=${t===this._clientVlanFilter}>${t}</option>`)}
            </select>
          </label>
          <label
            >SSID
            <select
              .value=${this._clientSsidFilter}
              @change=${t=>{this._clientSsidFilter=t.target.value,this._clientPage=0}}
            >
              <option value="">All</option>
              ${s.map(t=>B`<option value=${t} ?selected=${t===this._clientSsidFilter}>${t}</option>`)}
            </select>
          </label>
          ${this._clientVlanFilter?B`<span class="active-filter" @click=${()=>this._clientVlanFilter=""}
                >VLAN ${this._clientVlanFilter} ✕</span
              >`:W}
          ${this._clientSsidFilter?B`<span class="active-filter" @click=${()=>this._clientSsidFilter=""}
                >SSID ${this._clientSsidFilter} ✕</span
              >`:W}
        </div>
        <div class="toolbar">
          <input
            type="text"
            placeholder="Search client, IP, MAC, SSID, integration…"
            .value=${this._clientSearch}
            @input=${t=>{this._clientSearch=t.target.value,this._clientPage=0}}
          />
        </div>
        ${0===i.length?B`<div class="empty">No clients match.</div>`:B`
              <div class="table-wrap">
                <table>
                  <thead>
                    ${this._colHeaders()}
                  </thead>
                  <tbody>
                    ${a.map(t=>this._renderRow(t))}
                  </tbody>
                </table>
              </div>
              ${this._renderPager(i.length,this._clientPage,this._clientPageSize,t=>this._clientPage=t,t=>{this._clientPageSize=t,this._clientPage=0})}
            `}
        <div class="note">
          Columns shown as “—” aren't reported by this controller's API for that row.
          VLAN, IPv6, SSID, bandwidth, and last-seen availability depend on the UniFi
          firmware/API version.
        </div>
      </div>
    `}_renderDevicesTable(t){const e=Dt(this._filter(t.devices,this._deviceSearch),this._deviceSort,ge.DEVICE_SORT),s=this._paginate(e,this._devicePage,this._devicePageSize),i=this._deviceSort,a=t=>{this._deviceSort=t,this._devicePage=0};return B`
      <div class="card">
        <h3>Network Devices (${e.length})</h3>
        <div class="toolbar">
          <input
            type="text"
            placeholder="Search device, IP, MAC, integration…"
            .value=${this._deviceSearch}
            @input=${t=>{this._deviceSearch=t.target.value,this._devicePage=0}}
          />
        </div>
        ${0===e.length?B`<div class="empty">No network devices match.</div>`:B`
              <div class="table-wrap">
                <table>
                  <thead>
                    <tr>
                      ${Ut("Device","name",i,a)}
                      ${Ut("IPv4","ipv4",i,a)}
                      ${Ut("MAC","mac",i,a)}
                      ${Ut("VLAN","vlan",i,a,{numeric:!0})}
                      ${Ut("Model","model",i,a)}
                      ${Ut("Firmware","firmware",i,a)}
                      ${Ut("Bandwidth","bandwidth",i,a)}
                      ${Ut("Last Seen","last_seen",i,a)}
                      ${Ut("Integration","integration",i,a)}
                    </tr>
                  </thead>
                  <tbody>
                    ${s.map(t=>this._renderDeviceRow(t))}
                  </tbody>
                </table>
              </div>
              ${this._renderPager(e.length,this._devicePage,this._devicePageSize,t=>this._devicePage=t,t=>{this._devicePageSize=t,this._devicePage=0})}
            `}
      </div>
    `}_renderFirmware(t){return null==t?B`<span class="muted">—</span>`:t?B`<span style="color:var(--status-warning);font-weight:600;">Update available</span>`:B`<span class="muted">Up to date</span>`}_renderDeviceRow(t){return B`
      <tr>
        <td>
          <div style="font-weight:600;">${t.name}</div>
          ${t.state?B`<div class="muted" style="font-size:11px;">${t.state.toLowerCase()}</div>`:W}
        </td>
        <td class="mono">${t.ipv4??"—"}</td>
        <td class="mono">${t.mac??"—"}</td>
        <td class="num">${this._fmtVlan(t.vlan)}</td>
        <td>${t.model??"—"}</td>
        <td>${this._renderFirmware(t.firmware_updatable)}</td>
        <td>${this._fmtBandwidth(t.bandwidth)}</td>
        <td>${this._fmtLastSeen(t.last_seen)}</td>
        <td>${this._renderMatch(t)}</td>
      </tr>
    `}_renderPager(t,e,s,i,a){const r="all"===s?1:Math.max(1,Math.ceil(t/s));return B`
      <div class="footer">
        <button class="ha-btn" ?disabled=${e<=0} @click=${()=>i(e-1)}>Prev</button>
        <span>Page ${e+1} of ${r}</span>
        <button class="ha-btn" ?disabled=${e>=r-1} @click=${()=>i(e+1)}>
          Next
        </button>
        <select
          @change=${t=>{const e=t.target.value;a("all"===e?"all":Number(e))}}
        >
          ${_e.map(t=>B`<option value=${String(t)} ?selected=${t===s}>${"all"===t?"All":`${t} / page`}</option>`)}
        </select>
      </div>
    `}_renderProtectCard(t){const e=t.protect;return e.configured?e.reachable?B`
      <div class="card">
        <h3>
          UniFi Protect
          <span class="muted" style="font-weight:400;font-size:12px;">
            —
            <span class="dot ${e.cameras_online===e.camera_count?"good":"bad"}"></span>
            ${e.cameras_online} / ${e.camera_count} cameras online
          </span>
        </h3>
        ${this._renderProtectDevices(e.cameras)}
      </div>
      ${this._renderProtectEvents(e)}
    `:B`
        <div class="card">
          <h3>UniFi Protect</h3>
          <div class="muted" style="font-size:13px;">
            Configured but not reachable${e.error?B` — ${e.error}`:""}.
          </div>
        </div>
      `:W}_renderProtectDevices(t){if(!t.length)return B`<div class="empty">No Protect devices reported.</div>`;const e=this._protectSort,s=t=>this._protectSort=t,i=Dt(t.slice(),e,{name:t=>t.name,ip:t=>t.ip,mac:t=>t.mac,recording:t=>t.is_recording,last_ring:t=>t.last_ring,channels:t=>t.channel_count});return B`
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              ${Ut("Name","name",e,s)}
              ${Ut("IP","ip",e,s)}
              ${Ut("MAC","mac",e,s)}
              ${Ut("Recording","recording",e,s)}
              ${Ut("Last Ring","last_ring",e,s)}
              ${Ut("Channels","channels",e,s)}
              <th></th>
            </tr>
          </thead>
          <tbody>
            ${i.map(t=>{const e=ve(t.link);return B`
                <tr>
                  <td>
                    <div style="font-weight:600;">
                      ${e?B`<a class="thumb-link" href=${e} target="_blank" rel="noopener"
                            >${t.name} ↗</a
                          >`:t.name}
                    </div>
                    ${t.state?B`<div class="muted" style="font-size:11px;">${t.state.toLowerCase()}</div>`:W}
                  </td>
                  <td class="mono">${t.ip??"—"}</td>
                  <td class="mono">${t.mac??"—"}</td>
                  <td>
                    ${null==t.is_recording?B`<span class="muted">—</span>`:t.is_recording?B`<span class="dot bad"></span>Recording`:B`<span class="muted">Off</span>`}
                  </td>
                  <td>${this._fmtLastSeen(t.last_ring)}</td>
                  <td title=${t.channels.join(", ")}>
                    ${t.channel_count?`${t.channel_count}${t.channels.length?` (${t.channels.join(", ")})`:""}`:"—"}
                  </td>
                  <td>
                    ${e?B`<a class="thumb-link" href=${e} target="_blank" rel="noopener">Open ↗</a>`:W}
                  </td>
                </tr>
              `})}
          </tbody>
        </table>
      </div>
      <div class="note">
        Device names link to that camera on the Protect console
        (<code>https://&lt;host&gt;/protect/dashboard/devices/&lt;id&gt;</code>).
      </div>
    `}_fmtDuration(t){if(null==t)return"—";if(t<60)return`${t}s`;const e=Math.floor(t/60);if(e<60)return`${e}m ${t%60}s`;return`${Math.floor(e/60)}h ${e%60}m`}_renderProtectEvents(t){return B`
      <div class="card">
        <h3>Events &amp; AI Smart Detections <span class="muted" style="font-weight:400;font-size:12px;">— last 24h</span></h3>
        ${t.events_error?B`<div class="note" style="font-size:13px;">${t.events_error}</div>`:t.events.length?B`
                <div class="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        ${Ut("Type","type",this._eventSort,t=>this._eventSort=t)}
                        ${Ut("Smart Detections","detections",this._eventSort,t=>this._eventSort=t)}
                        ${Ut("Score","score",this._eventSort,t=>this._eventSort=t,{numeric:!0})}
                        ${Ut("Start","start",this._eventSort,t=>this._eventSort=t)}
                        ${Ut("Duration","duration",this._eventSort,t=>this._eventSort=t,{numeric:!0})}
                        <th>Thumbnail</th>
                        ${Ut("License Plate","plate",this._eventSort,t=>this._eventSort=t)}
                      </tr>
                    </thead>
                    <tbody>
                      ${Dt(t.events.slice(),this._eventSort,{type:t=>t.type,detections:t=>t.smart_detect_types.join(", ")||null,score:t=>t.score,start:t=>t.start,duration:t=>t.duration,plate:t=>t.license_plate}).map(t=>B`
                          <tr>
                            <td>${t.type??"—"}</td>
                            <td>
                              ${t.smart_detect_types.length?B`<span class="chips"
                                    >${t.smart_detect_types.map(t=>B`<span class="chip">${t}</span>`)}</span
                                  >`:B`<span class="muted">—</span>`}
                            </td>
                            <td class="num">${null==t.score?"—":t.score}</td>
                            <td>${this._fmtLastSeen(t.start)}</td>
                            <td class="num">${this._fmtDuration(t.duration)}</td>
                            <td>
                              ${ve(t.thumbnail_link)?B`<a
                                    class="thumb-link"
                                    href=${ve(t.thumbnail_link)}
                                    target="_blank"
                                    rel="noopener"
                                    >view ↗</a
                                  >`:t.thumbnail?B`<span class="muted" title="Thumbnail exists but needs an authenticated fetch">available</span>`:B`<span class="muted">—</span>`}
                            </td>
                            <td>${t.license_plate?B`<span class="plate">${t.license_plate}</span>`:B`<span class="muted">—</span>`}</td>
                          </tr>
                        `)}
                    </tbody>
                  </table>
                </div>
              `:B`<div class="empty">No events in the last 24 hours.</div>`}
      </div>
    `}};me.styles=[Ft,o`
      .stat-row {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 12px;
        margin-bottom: 16px;
      }
      .stat-tile {
        background: var(--card-background-color, #fff);
        border-radius: var(--ha-card-border-radius, 12px);
        box-shadow: var(--ha-card-box-shadow, 0 1px 2px rgba(0, 0, 0, 0.08));
        padding: 14px 16px;
        display: flex;
        flex-direction: column;
        gap: 6px;
      }
      .stat-tile .label {
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.03em;
        color: var(--secondary-text-color);
      }
      .stat-tile .value {
        font-size: 26px;
        font-weight: 700;
        line-height: 1.1;
      }
      .stat-tile .sub {
        font-size: 12px;
        color: var(--secondary-text-color);
      }
      .dot {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        margin-right: 6px;
        vertical-align: middle;
      }
      .dot.good {
        background: var(--status-good);
      }
      .dot.bad {
        background: var(--status-critical);
      }
      .dot.unknown {
        background: var(--cat-other);
      }
      .ssid-list {
        display: flex;
        flex-direction: column;
        gap: 8px;
      }
      .ssid-row {
        display: flex;
        align-items: center;
        gap: 10px;
        font-size: 13px;
      }
      .ssid-row .name {
        min-width: 140px;
        font-weight: 600;
      }
      .ssid-row .bar {
        flex: 1;
        height: 8px;
        border-radius: 4px;
        background: rgba(var(--rgb-primary-text-color, 0, 0, 0), 0.06);
        overflow: hidden;
      }
      .ssid-row .bar > span {
        display: block;
        height: 100%;
        background: var(--primary-color);
      }
      .ssid-row .count {
        min-width: 32px;
        text-align: right;
        font-variant-numeric: tabular-nums;
        font-weight: 700;
      }
      .ssid-row.clickable {
        cursor: pointer;
        border-radius: 6px;
        padding: 4px 6px;
        margin: -4px -6px;
      }
      .ssid-row.clickable:hover {
        background: rgba(var(--rgb-primary-text-color, 0, 0, 0), 0.04);
      }
      .ssid-row.active {
        background: rgba(var(--rgb-primary-color, 3, 155, 229), 0.12);
      }
      .ssid-row.active .name {
        color: var(--primary-color);
      }
      .filters {
        display: flex;
        gap: 8px;
        align-items: center;
        flex-wrap: wrap;
        margin-bottom: 10px;
      }
      .filters label {
        font-size: 12px;
        color: var(--secondary-text-color);
        display: inline-flex;
        align-items: center;
        gap: 6px;
      }
      .active-filter {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-size: 12px;
        background: var(--primary-color);
        color: #fff;
        padding: 4px 10px;
        border-radius: 100px;
        cursor: pointer;
      }
      .thumb-link {
        color: var(--primary-color);
        cursor: pointer;
        text-decoration: none;
      }
      .plate {
        font-family: var(--code-font-family, monospace);
        font-weight: 700;
        letter-spacing: 0.06em;
        background: rgba(var(--rgb-primary-text-color, 0, 0, 0), 0.06);
        padding: 2px 6px;
        border-radius: 4px;
      }
      .table-wrap {
        overflow-x: auto;
      }
      .toolbar input {
        flex: 1;
        min-width: 180px;
      }
      td.num,
      th.num {
        text-align: right;
        font-variant-numeric: tabular-nums;
      }
      .mono {
        font-family: var(--code-font-family, monospace);
        font-size: 12px;
      }
      .match {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        font-size: 11px;
        font-weight: 600;
        padding: 3px 8px;
        border-radius: 100px;
        cursor: pointer;
      }
      .match.failing {
        background: rgba(var(--rgb-error-color, 219, 68, 55), 0.15);
        color: var(--error-color, #db4437);
      }
      .match.healthy {
        background: rgba(67, 160, 71, 0.15);
        color: var(--success-color, #43a047);
      }
      .match.other {
        background: rgba(var(--rgb-primary-text-color, 0, 0, 0), 0.06);
        color: var(--secondary-text-color);
      }
      .alert {
        background: rgba(var(--rgb-error-color, 219, 68, 55), 0.1);
        border: 1px solid var(--error-color, #db4437);
        border-radius: 10px;
        padding: 12px 16px;
        margin-bottom: 16px;
        font-size: 13.5px;
        color: var(--primary-text-color);
        line-height: 1.5;
      }
      .footer {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-top: 10px;
        font-size: 12.5px;
        color: var(--secondary-text-color);
      }
      .footer select {
        margin-left: auto;
      }
      .note {
        font-size: 11.5px;
        color: var(--secondary-text-color);
        margin-top: 8px;
        line-height: 1.5;
      }
    `],me.CLIENT_SORT={name:t=>t.name,ipv4:t=>t.ipv4,ipv6:t=>t.ipv6,mac:t=>t.mac,vlan:t=>null==t.vlan||""===t.vlan?null:Number(t.vlan),ssid:t=>t.ssid??(t.wired?"wired":null),uptime:t=>t.uptime,bandwidth:t=>t.bandwidth?.total_bytes??null,last_seen:t=>t.last_seen,integration:t=>t.integration_match?.domain??null},me.DEVICE_SORT={name:t=>t.name,ipv4:t=>t.ipv4,mac:t=>t.mac,vlan:t=>null==t.vlan||""===t.vlan?null:Number(t.vlan),model:t=>t.model,firmware:t=>t.firmware_updatable,bandwidth:t=>t.bandwidth?.total_bytes??null,last_seen:t=>t.last_seen,integration:t=>t.integration_match?.domain??null},t([ht({attribute:!1})],me.prototype,"initialClientFilter",void 0),t([ut()],me.prototype,"_overview",void 0),t([ut()],me.prototype,"_loading",void 0),t([ut()],me.prototype,"_error",void 0),t([ut()],me.prototype,"_clientSearch",void 0),t([ut()],me.prototype,"_clientPage",void 0),t([ut()],me.prototype,"_clientPageSize",void 0),t([ut()],me.prototype,"_clientVlanFilter",void 0),t([ut()],me.prototype,"_clientSsidFilter",void 0),t([ut()],me.prototype,"_clientSort",void 0),t([ut()],me.prototype,"_deviceSearch",void 0),t([ut()],me.prototype,"_devicePage",void 0),t([ut()],me.prototype,"_devicePageSize",void 0),t([ut()],me.prototype,"_deviceSort",void 0),t([ut()],me.prototype,"_protectSort",void 0),t([ut()],me.prototype,"_eventSort",void 0),me=ge=t([dt("ha-soc-network-view")],me);const ye=/^([0-9a-f]{1,2}:){5}[0-9a-f]{1,2}$/i;function be(t){const e=t.split(".");if(4!==e.length)return null;let s=0;for(const t of e){if(!/^\d{1,3}$/.test(t))return null;const e=Number(t);if(e>255)return null;s=s<<8|e}return s>>>0}function fe(t,e){const s=e.indexOf("/");if(s<0)return!1;const i=e.slice(0,s),a=Number(e.slice(s+1));if(!Number.isInteger(a)||a<0||a>32)return!1;const r=be(t),o=be(i);if(null===r||null===o)return!1;const n=0===a?0:4294967295<<32-a>>>0;return(r&n)===(o&n)}function $e(t,e){const s=[];if(ye.test(t)){const i=t.toLowerCase();for(const a of e)a.mac&&a.mac.toLowerCase()===i&&s.push({name:a.name||a.mac,matchedOn:t});return s}if(t.includes("/")){for(const i of e)i.ipv4&&fe(i.ipv4,t)&&s.push({name:i.name||i.ipv4,matchedOn:i.ipv4});return s}for(const i of e)i.ipv4!==t&&i.ipv6!==t||s.push({name:i.name||t,matchedOn:t});return s}let we=class extends Ot{constructor(){super(...arguments),this._overview=null,this._loading=!0,this._error=null,this._aclSort=null,this._firewallPolicySort=null,this._portSort=null,this._fwViewMode="table",this._fwZonePairFilter=null}get viewId(){return"network_security"}connectedCallback(){super.connectedCallback(),this._load()}async _load(){this._loading=!0,this._error=null;try{this._overview=await(t=this.hass,gt(t,{type:"ha_soc/network_security/overview"}))}catch(t){this._error=t instanceof Error?t.message:String(t),this._overview=null}finally{this._loading=!1}var t}render(){if(this._loading)return B`<div class="card">Loading…</div>`;if(this._error)return B`<div class="card"><div class="alert">${this._error}</div></div>`;const t=this._overview;if(!t)return B`<div class="card">No data.</div>`;const e=[{id:"findings",title:"Suggestions",render:()=>this._renderFindings(t.findings)},{id:"firewall_policies",title:"Firewall Policies",render:()=>this._renderFirewallPolicies(t.firewall_policies)},{id:"acl",title:"ACL Rules",render:()=>this._renderAcl(t.acl)},{id:"server_ports",title:"Home Assistant Server Ports",render:()=>this._renderServerPorts(t.server_ports)},{id:"pihole",title:"Pi-hole DNS",render:()=>this._renderPihole(t.pihole)}];return B`
      <div class="toolbar" style="margin-bottom:12px;display:flex;gap:8px;align-items:center;">
        <button class="ha-btn" @click=${()=>this._load()}>Refresh</button>
        <span class="muted" style="font-size:12px;">
          Advisory only — nothing on this tab changes UniFi or Pi-hole configuration.
        </span>
      </div>
      ${this._renderSections(e)}
    `}_renderFindings(t){return B`
      <div class="card">
        <h3>Suggestions</h3>
        ${t.length?B`${t.map(t=>B`
                <div class="finding">
                  <div class="sev ${t.severity}" title=${t.severity}></div>
                  <div>
                    <div class="finding-title">${t.title}</div>
                    <div class="finding-detail">${t.detail}</div>
                  </div>
                </div>
              `)}`:B`<div class="empty">Nothing stood out — no advisory findings right now.</div>`}
      </div>
    `}_renderCustomBadge(t){return t?B`<span class="badge-custom">custom</span>`:W}_customCountLabel(t){const e=t.filter(t=>null!=t.custom);if(!e.length)return"";const s=e.filter(t=>t.custom).length;return` · ${s} custom / ${t.length} total`}_renderDeviceChips(t){const e=function(t,e){if(!t.length||!e.length)return[];const s=new Set,i=[];for(const a of t)for(const t of $e(a,e)){const e=`${t.name}\0${t.matchedOn}`;s.has(e)||(s.add(e),i.push(t))}return i}(t,this._overview?.clients??[]),s=e.slice(0,6);if(!s.length)return W;const i=e.length-s.length;return B`
      <span class="sub" style="display:block;margin-top:3px;">
        ${s.map(t=>B`
            <button
              class="device-chip"
              title="Jump to ${t.name} on the Network tab"
              @click=${()=>ee(this,"network",t.matchedOn)}
            >
              📟 ${t.name}
            </button>
          `)}${i>0?B`<span class="muted" style="font-size:10.5px;">+${i} more</span>`:W}
      </span>
    `}_policyActionClass(t){const e=(t??"").toLowerCase();return"allow"===e?"healthy":"block"===e||"reject"===e?"failing":"other"}_renderFirewallPolicies(t){const e=this._fwZonePairFilter?t.rules.filter(t=>t.source.zone===this._fwZonePairFilter.src&&t.destination.zone===this._fwZonePairFilter.dst):t.rules;return B`
      <div class="card">
        <h3>
          Firewall Policies — Security Audit
          <span class="muted" style="font-weight:400;font-size:12px;"
            >— UniFi's default zone-based allow/deny view; order matters, evaluated top
            to bottom${this._customCountLabel(t.rules)}</span
          >
        </h3>
        ${t.available?t.rules.length?B`
                <div class="view-toggle">
                  <button
                    class=${"table"===this._fwViewMode?"active":""}
                    @click=${()=>this._fwViewMode="table"}
                  >
                    Table
                  </button>
                  <button
                    class=${"matrix"===this._fwViewMode?"active":""}
                    @click=${()=>this._fwViewMode="matrix"}
                  >
                    Zone Matrix
                  </button>
                </div>
                ${"matrix"===this._fwViewMode?this._renderZoneMatrix(t):this._renderFirewallPolicyTable(e)}
              `:B`<div class="empty">No Firewall Policies configured.</div>`:B`
              <div class="note" style="font-size:13px;">
                Couldn't read Firewall Policies from this controller.${t.error?B` ${t.error}`:""}
              </div>
            `}
      </div>
    `}_renderFirewallPolicyTable(t){return B`
      ${this._fwZonePairFilter?B`
            <div class="zone-pair-filter">
              <span class="chip"
                >${this._fwZonePairFilter.src} → ${this._fwZonePairFilter.dst}</span
              >
              <button
                style="cursor:pointer;border:none;background:none;color:var(--primary-color);font-size:12px;"
                @click=${()=>this._fwZonePairFilter=null}
              >
                Clear filter
              </button>
            </div>
          `:W}
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              ${Ut("#","order",this._firewallPolicySort,t=>this._firewallPolicySort=t,{numeric:!0})}
              ${Ut("Name","name",this._firewallPolicySort,t=>this._firewallPolicySort=t)}
              ${Ut("Action","action",this._firewallPolicySort,t=>this._firewallPolicySort=t)}
              ${Ut("Source zone","source_zone",this._firewallPolicySort,t=>this._firewallPolicySort=t)}
              ${Ut("Dest. zone","dest_zone",this._firewallPolicySort,t=>this._firewallPolicySort=t)}
              ${Ut("Protocol","protocol",this._firewallPolicySort,t=>this._firewallPolicySort=t)}
              ${Ut("Ports","ports",this._firewallPolicySort,t=>this._firewallPolicySort=t)}
              ${Ut("Enabled","enabled",this._firewallPolicySort,t=>this._firewallPolicySort=t)}
            </tr>
          </thead>
          <tbody>
            ${t.length?Dt(t.slice(),this._firewallPolicySort,{order:t=>t.order,name:t=>t.name,action:t=>t.action,source_zone:t=>t.source.zone,dest_zone:t=>t.destination.zone,protocol:t=>t.protocol,ports:t=>t.ports.length,enabled:t=>t.enabled}).map((t,e)=>this._renderFirewallPolicyRow(t,e)):B`<tr><td colspan="8"><div class="empty">No policies for this zone pair.</div></td></tr>`}
          </tbody>
        </table>
      </div>
      <div class="note">
        Every policy is scoped to a source/destination zone pair; the detail line under
        each name shows any additional network/IP/MAC/domain narrowing the controller
        reported, and a resolved device chip when it matches a known client.
      </div>
    `}_renderZoneMatrix(t){if(!t.zones.length)return B`<div class="empty">No firewall zones reported by this controller.</div>`;const e=function(t,e){const s=t.map(t=>t.name);return s.map(t=>s.map(s=>{const i=e.filter(e=>e.source.zone===t&&e.destination.zone===s),a=i.filter(t=>!1!==t.enabled),r=a.filter(t=>"ALLOW"===t.action).length,o=a.filter(t=>"BLOCK"===t.action||"REJECT"===t.action).length;let n="none";return r&&o?n="mixed":r?n="allow":o&&(n="block"),{srcZone:t,dstZone:s,policies:i,allowCount:r,blockCount:o,dominant:n}}))}(t.zones,t.rules),s=t.zones.map(t=>t.name);return B`
      <div class="matrix-wrap">
        <table class="zone-matrix">
          <thead>
            <tr>
              <th class="corner"></th>
              ${s.map(t=>B`<th>${t}</th>`)}
            </tr>
          </thead>
          <tbody>
            ${e.map((t,e)=>B`
                <tr>
                  <th>${s[e]}</th>
                  ${t.map(t=>B`
                      <td
                        class="cell ${t.dominant}"
                        title="${t.policies.length} polic${1===t.policies.length?"y":"ies"}"
                        @click=${()=>this._selectZonePair(t.srcZone,t.dstZone)}
                      >
                        ${"none"===t.dominant?"—":"mixed"===t.dominant?"mixed":"allow"===t.dominant?"allow":"block"}${t.policies.length?B`<br /><span style="font-size:10px;">${t.policies.length}</span>`:W}
                      </td>
                    `)}
                </tr>
              `)}
          </tbody>
        </table>
      </div>
      <div class="note">
        Rows are the source zone, columns the destination zone. Click a cell to see its
        policies. "mixed" means both allow and block/reject policies exist for that pair
        — which one actually governs a given connection depends on evaluation order and
        UniFi's own implicit-deny fallback, neither of which this project models; open
        the filtered table to read the real order.
      </div>
    `}_selectZonePair(t,e){this._fwZonePairFilter={src:t,dst:e},this._fwViewMode="table"}_renderFirewallPolicyRow(t,e){const s=t=>{const e=[];return t.networks.length&&e.push(`networks: ${t.networks.join(", ")}`),t.ip_or_subnets.length&&e.push(`IP: ${t.ip_or_subnets.join(", ")}`),t.macs.length&&e.push(`MAC: ${t.macs.join(", ")}`),t.domains.length&&e.push(`domains: ${t.domains.join(", ")}`),t.applications.length&&e.push(`${t.applications.length} app(s)`),t.application_categories.length&&e.push(`${t.application_categories.length} app categor${1===t.application_categories.length?"y":"ies"}`),!e.length&&t.filter_type&&e.push(t.filter_type.toLowerCase().replace(/_/g," ")),e.join(" · ")},i=s(t.source),a=s(t.destination),r=[i&&`from ${i}`,a&&`to ${a}`].filter(Boolean).join(" · "),o=[...t.source.ip_or_subnets,...t.source.macs,...t.destination.ip_or_subnets,...t.destination.macs];return B`
      <tr>
        <td class="num">${t.order??e+1}</td>
        <td style="font-weight:600;">
          ${t.name??"—"}${this._renderCustomBadge(t.custom)}${r?B`<span class="sub">${r}</span>`:W}${this._renderDeviceChips(o)}
        </td>
        <td>
          ${t.action?B`<span class="match ${this._policyActionClass(t.action)}">${t.action}</span>`:B`<span class="muted">—</span>`}${t.allow_return_traffic?B`<span class="sub">+ mirrored return-traffic policy</span>`:W}
        </td>
        <td>${t.source.zone??B`<span class="muted">—</span>`}</td>
        <td>${t.destination.zone??B`<span class="muted">—</span>`}</td>
        <td>${t.protocol??B`<span class="muted">any</span>`}</td>
        <td>
          ${t.ports.length?B`<span class="mono">${t.ports.join(", ")}</span>`:t.source.ports_from_list||t.destination.ports_from_list?B`<span class="muted">traffic matching list</span>`:B`<span class="muted">any</span>`}
        </td>
        <td>
          ${null==t.enabled?B`<span class="muted">—</span>`:t.enabled?"yes":B`<span class="muted">disabled</span>`}
        </td>
      </tr>
    `}_aclActionClass(t){const e=(t??"").toLowerCase();return["allow","accept","permit"].some(t=>e.includes(t))?"healthy":["deny","drop","block","reject"].some(t=>e.includes(t))?"failing":"other"}_renderAcl(t){return B`
      <div class="card" id="acl-card">
        <h3>
          ACL Rules — Security Audit
          <span class="muted" style="font-weight:400;font-size:12px;"
            >— order matters; rules are evaluated top to bottom${t.endpoint?` · source: ${t.endpoint}`:""}${this._customCountLabel(t.rules)}</span
          >
        </h3>
        ${t.available?t.rules.length?B`
                <div class="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        ${Ut("#","order",this._aclSort,t=>this._aclSort=t,{numeric:!0})}
                        ${Ut("Name","name",this._aclSort,t=>this._aclSort=t)}
                        ${Ut("Action","action",this._aclSort,t=>this._aclSort=t)}
                        ${Ut("Protocols","protocols",this._aclSort,t=>this._aclSort=t)}
                        ${Ut("Networks","networks",this._aclSort,t=>this._aclSort=t)}
                        ${Ut("Ports","ports",this._aclSort,t=>this._aclSort=t,{numeric:!0})}
                        ${Ut("Enabled","enabled",this._aclSort,t=>this._aclSort=t)}
                      </tr>
                    </thead>
                    <tbody>
                      ${Dt(t.rules.slice(),this._aclSort,{order:t=>t.order,name:t=>t.name,action:t=>t.action,protocols:t=>t.protocols.join(", ")||null,networks:t=>t.networks.join(", ")||null,ports:t=>t.ports.length,enabled:t=>t.enabled}).map((t,e)=>this._renderAclRow(t,e))}
                    </tbody>
                  </table>
                </div>
                <div class="note">
                  Order reflects evaluation precedence as returned by the controller. Source
                  and destination detail (IP/subnet, MAC, port scoping) is shown under each
                  rule's name when the controller reported it.
                </div>
              `:B`<div class="empty">No ACL rules configured (endpoint: ${t.endpoint}).</div>`:B`
              <div class="note" style="font-size:13px;">
                This controller's Integration API didn't return ACL rules. Endpoints tried:
                <code>${t.endpoints_tried.join(", ")||"—"}</code>.${t.error?B` Last response: ${t.error}.`:""}
              </div>
            `}
      </div>
    `}_renderAclRow(t,e){const s=[];t.source.ip_or_subnets.length&&s.push(`from ${t.source.ip_or_subnets.join(", ")}`),t.source.macs.length&&s.push(`MAC ${t.source.macs.join(", ")}`);const i=[];t.destination.ip_or_subnets.length&&i.push(`to ${t.destination.ip_or_subnets.join(", ")}`),t.destination.macs.length&&i.push(`MAC ${t.destination.macs.join(", ")}`);const a=[...s,...i].join(" · "),r=[...t.source.ip_or_subnets,...t.source.macs,...t.destination.ip_or_subnets,...t.destination.macs];return B`
      <tr>
        <td class="num">${t.order??e+1}</td>
        <td style="font-weight:600;">
          ${t.name??"—"}${this._renderCustomBadge(t.custom)}${a?B`<span class="sub">${a}</span>`:W}${this._renderDeviceChips(r)}
        </td>
        <td>
          ${t.action?B`<span class="match ${this._aclActionClass(t.action)}">${t.action}</span>`:B`<span class="muted">—</span>`}
        </td>
        <td>${t.protocols.length?t.protocols.join(", "):B`<span class="muted">any</span>`}</td>
        <td>
          ${t.networks.length?B`<span class="chips">${t.networks.map(t=>B`<span class="chip">${t}</span>`)}</span>`:B`<span class="muted">any / —</span>`}
        </td>
        <td>
          ${t.ports.length?B`<span class="mono">${t.ports.join(", ")}</span>`:B`<span class="muted">any</span>`}
        </td>
        <td>
          ${null==t.enabled?B`<span class="muted">—</span>`:t.enabled?"yes":B`<span class="muted">disabled</span>`}
        </td>
      </tr>
    `}_portStatusClass(t){return"covered"===t?"healthy":"uncovered"===t?"failing":"other"}_renderServerPorts(t){return B`
      <div class="card">
        <h3>
          Home Assistant Server Ports
          <span class="muted" style="font-weight:400;font-size:12px;"
            >— cross-referenced against the ACL rules above</span
          >
        </h3>
        ${t.available?B`
              <div class="table-wrap">
                <table>
                  <thead>
                    <tr>
                      ${Ut("Port","port",this._portSort,t=>this._portSort=t,{numeric:!0})}
                      ${Ut("Proto","proto",this._portSort,t=>this._portSort=t)}
                      ${Ut("Address","address",this._portSort,t=>this._portSort=t)}
                      ${Ut("Process","process",this._portSort,t=>this._portSort=t)}
                      ${Ut("Coverage","status",this._portSort,t=>this._portSort=t)}
                    </tr>
                  </thead>
                  <tbody>
                    ${Dt(t.ports.slice(),this._portSort,{port:t=>t.port,proto:t=>t.proto,address:t=>t.address,process:t=>t.process,status:t=>t.status}).map(t=>B`
                        <tr>
                          <td class="num">${t.port}</td>
                          <td>${t.proto??"—"}</td>
                          <td class="mono">${t.address??"—"}</td>
                          <td>${t.process??"—"}</td>
                          <td>
                            <span class="match ${this._portStatusClass(t.status)}">
                              ${"covered"===t.status?`covered by ${t.covered_by.join(", ")}`:"network_scoped"===t.status?`network-scoped: ${t.network_scoped_by.join(", ")}`:"uncovered"}
                            </span>
                          </td>
                        </tr>
                      `)}
                  </tbody>
                </table>
              </div>
              <div class="note">
                "Uncovered" means no enabled ACL rule names this server's IP/subnet as a
                destination for that port — it does not by itself mean the port is reachable
                from every network; UniFi's own default zone policy still applies.
                "Network-scoped" means a rule covers it by network/zone rather than by IP,
                which this project can't independently verify covers this server.
              </div>
            `:B`
              <div class="empty">
                No listening-port report from the HA SOC Probe add-on yet, or none of its
                reported bind addresses are real LAN addresses. Install/enable the Probe
                add-on to populate this.
              </div>
            `}
      </div>
    `}_renderPihole(t){return t.configured?t.reachable?B`
      <div class="card">
        <h3>Pi-hole DNS</h3>
        <div class="stat-row">
          <div class="stat-tile">
            <span class="label">Blocking</span>
            <span class="value">${t.blocking_enabled?"On":"Off"}</span>
          </div>
          <div class="stat-tile">
            <span class="label">Queries (24h window)</span>
            <span class="value">${t.summary?.total??"—"}</span>
          </div>
          <div class="stat-tile">
            <span class="label">Blocked</span>
            <span class="value"
              >${t.summary?.blocked??"—"}${null!=t.summary?.percent_blocked?` (${t.summary.percent_blocked.toFixed(1)}%)`:""}</span
            >
          </div>
          <div class="stat-tile">
            <span class="label">IoT subnet scoped</span>
            <span class="value">
              ${null==t.iot_cidr?B`<span class="muted" style="font-size:16px;">not set</span>`:t.iot_clients_scoped?"Yes":B`<span style="color:var(--status-warning, #fab219);">No</span>`}
            </span>
          </div>
        </div>
        ${t.top_blocked_domains.length||t.recent_blocked.length?B`
              <div class="stat-row" style="margin-top:12px;">
                ${t.top_blocked_domains.length?B`
                      <div class="stat-tile" style="grid-column: span 2;">
                        <span class="label">Top blocked domains</span>
                        <div class="domain-list">
                          ${t.top_blocked_domains.map(t=>B`<div class="row"><span>${t.domain}</span><span>${t.count}</span></div>`)}
                        </div>
                      </div>
                    `:W}
                ${t.recent_blocked.length?B`
                      <div class="stat-tile" style="grid-column: span 2;">
                        <span class="label">Recently blocked</span>
                        <div class="domain-list">
                          ${t.recent_blocked.map(t=>B`<div class="row"><span>${t}</span></div>`)}
                        </div>
                      </div>
                    `:W}
              </div>
            `:W}
      </div>
    `:B`
        <div class="card">
          <h3>Pi-hole DNS</h3>
          <div class="alert">${t.error??"Pi-hole is not reachable."}</div>
        </div>
      `:B`
        <div class="card">
          <h3>Pi-hole DNS</h3>
          <div class="empty">
            Not connected. Add a Pi-hole host and app password in Settings to see blocking
            status, IoT client group scoping, and recently blocked domains here.
          </div>
        </div>
      `}};var xe;function ke(t){const e=t.match(/^homeassistant\.components\.([^.]+)/);if(e)return e[1];const s=t.match(/^custom_components\.([^.]+)/);return s?s[1]:t.split(".")[0]}we.styles=[Ft,o`
      .table-wrap {
        overflow-x: auto;
      }
      td.num,
      th.num {
        text-align: right;
        font-variant-numeric: tabular-nums;
      }
      .mono {
        font-family: var(--code-font-family, monospace);
        font-size: 12px;
      }
      .match {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        font-size: 11px;
        font-weight: 600;
        padding: 3px 8px;
        border-radius: 100px;
      }
      .match.failing {
        background: rgba(var(--rgb-error-color, 219, 68, 55), 0.15);
        color: var(--error-color, #db4437);
      }
      .match.healthy {
        background: rgba(67, 160, 71, 0.15);
        color: var(--success-color, #43a047);
      }
      .match.other {
        background: rgba(var(--rgb-primary-text-color, 0, 0, 0), 0.06);
        color: var(--secondary-text-color);
      }
      .chips {
        display: inline-flex;
        flex-wrap: wrap;
        gap: 4px;
      }
      .chip {
        background: rgba(var(--rgb-primary-text-color, 0, 0, 0), 0.06);
        border-radius: 100px;
        padding: 2px 8px;
        font-size: 11px;
      }
      .badge-custom {
        display: inline-block;
        margin-left: 6px;
        font-size: 10px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.03em;
        padding: 1px 7px;
        border-radius: 100px;
        background: rgba(var(--rgb-primary-color, 3, 155, 229), 0.15);
        color: var(--primary-color);
        vertical-align: middle;
      }
      .sub {
        display: block;
        font-size: 11px;
        color: var(--secondary-text-color);
        margin-top: 2px;
      }
      .note {
        font-size: 11.5px;
        color: var(--secondary-text-color);
        margin-top: 8px;
        line-height: 1.5;
      }
      .finding {
        display: flex;
        gap: 12px;
        padding: 10px 0;
        border-top: 1px solid var(--divider-color);
      }
      .finding:first-of-type {
        border-top: none;
      }
      .sev {
        flex: 0 0 auto;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        margin-top: 6px;
      }
      .sev.high {
        background: var(--status-critical, #d03b3b);
      }
      .sev.medium {
        background: var(--status-warning, #fab219);
      }
      .sev.info {
        background: var(--cat-other, #9aa0a6);
      }
      .finding-title {
        font-weight: 600;
        font-size: 13.5px;
      }
      .finding-detail {
        font-size: 12.5px;
        color: var(--secondary-text-color);
        margin-top: 3px;
        line-height: 1.5;
      }
      .stat-row {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 12px;
        margin-bottom: 4px;
      }
      .stat-tile {
        background: var(--card-background-color, #fff);
        border-radius: var(--ha-card-border-radius, 12px);
        box-shadow: var(--ha-card-box-shadow, 0 1px 2px rgba(0, 0, 0, 0.08));
        padding: 14px 16px;
        display: flex;
        flex-direction: column;
        gap: 6px;
      }
      .stat-tile .label {
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.03em;
        color: var(--secondary-text-color);
      }
      .stat-tile .value {
        font-size: 26px;
        font-weight: 700;
        line-height: 1.1;
      }
      .domain-list {
        display: flex;
        flex-direction: column;
        gap: 4px;
        font-size: 12.5px;
        max-height: 220px;
        overflow-y: auto;
      }
      .domain-list .row {
        display: flex;
        justify-content: space-between;
        gap: 8px;
        padding: 3px 0;
        border-bottom: 1px solid var(--divider-color);
      }
      .domain-list .row:last-child {
        border-bottom: none;
      }
      .view-toggle {
        display: inline-flex;
        border: 1px solid var(--divider-color);
        border-radius: 100px;
        overflow: hidden;
        margin-bottom: 10px;
      }
      .view-toggle button {
        border: none;
        background: var(--card-background-color, #fff);
        color: var(--primary-text-color);
        font-size: 12px;
        font-weight: 600;
        padding: 5px 14px;
        cursor: pointer;
      }
      .view-toggle button.active {
        background: var(--primary-color);
        color: #fff;
      }
      .device-chip {
        display: inline-flex;
        align-items: center;
        gap: 3px;
        background: rgba(var(--rgb-primary-color, 3, 155, 229), 0.1);
        color: var(--primary-color);
        border: none;
        border-radius: 100px;
        padding: 1px 8px;
        font-size: 10.5px;
        cursor: pointer;
        margin: 2px 3px 0 0;
      }
      .device-chip:hover {
        background: rgba(var(--rgb-primary-color, 3, 155, 229), 0.2);
      }
      .matrix-wrap {
        overflow-x: auto;
      }
      table.zone-matrix {
        border-collapse: collapse;
      }
      table.zone-matrix th,
      table.zone-matrix td {
        border: 1px solid var(--divider-color);
        padding: 6px;
        text-align: center;
        font-size: 11.5px;
      }
      table.zone-matrix th {
        background: rgba(var(--rgb-primary-text-color, 0, 0, 0), 0.03);
        font-weight: 600;
      }
      table.zone-matrix th.corner {
        background: transparent;
        border: none;
      }
      table.zone-matrix td.cell {
        cursor: pointer;
        min-width: 64px;
      }
      table.zone-matrix td.cell:hover {
        outline: 2px solid var(--primary-color);
        outline-offset: -2px;
      }
      table.zone-matrix td.cell.allow {
        background: rgba(67, 160, 71, 0.15);
        color: var(--success-color, #43a047);
      }
      table.zone-matrix td.cell.block {
        background: rgba(var(--rgb-error-color, 219, 68, 55), 0.15);
        color: var(--error-color, #db4437);
      }
      table.zone-matrix td.cell.mixed {
        background: rgba(var(--status-warning, #fab219), 0.18);
        color: #9a6a00;
      }
      table.zone-matrix td.cell.none {
        color: var(--secondary-text-color);
      }
      .zone-pair-filter {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 12.5px;
        margin-bottom: 10px;
      }
    `],t([ut()],we.prototype,"_overview",void 0),t([ut()],we.prototype,"_loading",void 0),t([ut()],we.prototype,"_error",void 0),t([ut()],we.prototype,"_aclSort",void 0),t([ut()],we.prototype,"_firewallPolicySort",void 0),t([ut()],we.prototype,"_portSort",void 0),t([ut()],we.prototype,"_fwViewMode",void 0),t([ut()],we.prototype,"_fwZonePairFilter",void 0),we=t([dt("ha-soc-network-security-view")],we);const Se=["DEBUG","INFO","WARNING","ERROR","CRITICAL"];const Ce="system";let Ae=xe=class extends Ot{constructor(){super(...arguments),this._entries=[],this._fault=null,this._loading=!0,this._error=null,this._domainFilter="",this._levelFilter="",this._expanded=new Set,this._sort=null,this._targets=null,this._source=Ce,this._containerLog=null,this._containerLoading=!1}get viewId(){return"logs"}connectedCallback(){super.connectedCallback(),this._load()}async _load(){this._loading=!0,this._error=null;try{const[e,s,i]=await Promise.all([(t=this.hass,gt(t,{type:"system_log/list"})),$t(this.hass),wt(this.hass).catch(()=>null)]);this._entries=e,this._fault=s,this._targets=i}catch(t){this._error=t?.message??String(t)}finally{this._loading=!1}var t}async _loadContainer(t){this._containerLoading=!0;try{this._containerLog=await((t,e)=>gt(t,{type:"ha_soc/logs/container",target:e}))(this.hass,t)}catch(e){this._containerLog={available:!1,target:t,content:null,truncated:!1,error:String(e),fetched_at:(new Date).toISOString()}}finally{this._containerLoading=!1}}_onSourceChange(t){const e=t.target.value;this._source=e,this._containerLog=null,e!==Ce&&this._loadContainer(e)}_refresh(){this._source===Ce?this._load():this._loadContainer(this._source)}_toggleExpanded(t){const e=new Set(this._expanded);e.has(t)?e.delete(t):e.add(t),this._expanded=e}get _domains(){return Array.from(new Set(this._entries.map(t=>ke(t.name)))).sort()}get _levels(){const t=new Set(this._entries.map(t=>t.level.toUpperCase()));return Se.filter(e=>t.has(e))}get _filtered(){const t=this._entries.filter(t=>(!this._domainFilter||ke(t.name)===this._domainFilter)&&(!this._levelFilter||t.level.toUpperCase()===this._levelFilter));return Dt(t,this._sort,xe.LOG_SORT)}_renderFaultLogCard(){const t=this._fault;return t?B`
      <div class="card fault-log">
        <h3>
          Home Assistant Crash Log
          ${t.exists&&t.content?.trim()?B`<span class="log-level critical"><span class="dot"></span>crash detected</span>`:B`<span class="tag enforced">none detected</span>`}
        </h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          <code>home-assistant.log.fault</code> — Python's own faulthandler dump. This
          file is only ever written when Home Assistant Core itself crashes at a fatal,
          low level (segfault, abort, illegal instruction) — a normal Python exception
          never creates it, and it's separate from the WARNING/ERROR table below. Home
          Assistant appends to this file across restarts and only deletes it automatically
          after a clean run finds it empty, so old content can persist here until it's
          cleared by hand on the host — this view is read-only and never touches the file.
        </p>
        ${t.exists&&t.content?.trim()?B`
              <p class="muted" style="font-size:12px;">
                Last written ${new Date(t.modified_at).toLocaleString()} —
                ${t.size_bytes.toLocaleString()} byte(s) total${t.truncated?", showing the most recent 64 KB":""}.
              </p>
              <pre>${t.content}</pre>
            `:B`<div class="empty">No crash detected.</div>`}
      </div>
    `:W}_renderContainerLog(){const t=this._containerLog,e=this._targets?.targets.find(t=>t.id===this._source)?.name??this._source;return this._containerLoading&&!t?B`<div class="empty">Loading ${e} logs…</div>`:t?t.available?B`
      <p class="muted" style="font-size:12px;">
        Fetched ${new Date(t.fetched_at).toLocaleString()}${t.truncated?", showing the most recent 128 KB (older lines are in the add-on's own Log tab)":""}.
        This is the container's live journald stream via Supervisor, point-in-time, use
        Refresh for new lines.
      </p>
      <pre class="rawlog">${t.content?.trim()?t.content:"(log is empty)"}</pre>
    `:B`<div class="empty">
        Couldn't load ${e} logs${t.error?B`<br /><span class="muted">${t.error}</span>`:W}
      </div>`:B`<div class="empty">Select a source.</div>`}render(){const t=this._filtered,e=this._sort,s=t=>{this._sort=t,this._expanded=new Set},i=this._source===Ce,a=[{id:"fault_log",title:"Home Assistant Crash Log",render:()=>this._renderFaultLogCard()},{id:"logs",title:"Logs",hideable:!1,render:()=>B`
      <div class="card">
        <h3>Logs</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          ${i?B`The same WARNING/ERROR/CRITICAL buffer as Settings → System → Logs
                (<code>/config/logs</code>), deduplicated, most recent first. This shows Home
                Assistant's own captured log records only. For an app or add-on's full
                container output, pick it from the source selector.`:B`Raw container output captured by the Supervisor, the same stream as the
                add-on's own Log tab. ANSI colors are stripped server-side.`}
        </p>
        <div class="toolbar">
          ${this._targets?.available?B`
                <select @change=${this._onSourceChange} aria-label="Log source">
                  <option value=${Ce} ?selected=${i}>
                    Integration logs (captured records)
                  </option>
                  ${this._targets.targets.map(t=>B`<option value=${t.id} ?selected=${t.id===this._source}>${t.name}</option>`)}
                </select>
              `:W}
          ${i?B`
                <select
                  aria-label="Filter by integration"
                  @change=${t=>{this._domainFilter=t.target.value,this._expanded=new Set}}
                >
                  <option value="" ?selected=${""===this._domainFilter}>All integrations</option>
                  ${this._domains.map(t=>B`<option value=${t} ?selected=${t===this._domainFilter}>${t}</option>`)}
                </select>
                <select
                  aria-label="Filter by level"
                  @change=${t=>{this._levelFilter=t.target.value,this._expanded=new Set}}
                >
                  <option value="" ?selected=${""===this._levelFilter}>All levels</option>
                  ${this._levels.map(t=>B`<option value=${t} ?selected=${t===this._levelFilter}>${t}</option>`)}
                </select>
              `:W}
          <span class="spacer"></span>
          <button class="ha-btn" @click=${this._refresh} ?disabled=${this._containerLoading}>
            ${this._containerLoading?"Loading…":"Refresh"}
          </button>
        </div>
        ${i?this._loading?B`<div class="empty">Loading…</div>`:this._error?B`
              <div style="border:1px solid var(--error-color,#db4437);border-radius:6px;padding:10px 12px;">
                <p style="font-size:13px;margin:0 0 8px;">${this._error}</p>
                <button class="ha-btn" @click=${()=>this._load()}>Retry</button>
              </div>
            `:t.length?B`
              <table>
                <thead>
                  <tr>
                    ${Ut("Time","time",e,s)}
                    ${Ut("Level","level",e,s)}
                    ${Ut("Integration","integration",e,s)}
                    ${Ut("Message","message",e,s)}
                    ${Ut("Count","count",e,s,{numeric:!0})}
                  </tr>
                </thead>
                <tbody>
                  ${t.map((t,e)=>{const s=this._expanded.has(e);return B`
                      <tr
                        class=${t.exception?"clickable":""}
                        title=${t.exception?"Click to show/hide the traceback":""}
                        @click=${()=>t.exception&&this._toggleExpanded(e)}
                      >
                        <td>${new Date(1e3*t.first_occurred).toLocaleString()}</td>
                        <td>
                          <span class="log-level ${function(t){const e=t.toUpperCase();return Se.includes(e)?e.toLowerCase():"info"}(t.level)}"
                            ><span class="dot"></span>${t.level}</span
                          >
                        </td>
                        <td class="muted">${ke(t.name)}</td>
                        <td>
                          ${t.message[t.message.length-1]}
                          ${t.source?B`<div class="muted" style="font-size:11px;">${t.source[0]}:${t.source[1]}</div>`:W}
                        </td>
                        <td class="num">${t.count}</td>
                      </tr>
                      ${s&&t.exception?B`
                            <tr>
                              <td colspan="5">
                                <pre
                                  style="white-space:pre-wrap;font-size:11.5px;background:rgba(var(--rgb-primary-text-color,0,0,0),0.04);padding:10px;border-radius:6px;margin:0;"
                                >
${t.exception}</pre
                                >
                              </td>
                            </tr>
                          `:W}
                    `})}
                </tbody>
              </table>
            `:B`<div class="empty">No matching log entries.</div>`:this._renderContainerLog()}
      </div>
        `}];return this._renderSections(a)}};var Pe;Ae.styles=[Ft,o`
      .log-level {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.02em;
        padding: 3px 8px;
        border-radius: 100px;
      }
      .log-level .dot {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        flex: none;
      }
      .log-level.debug {
        background: rgba(154, 160, 166, 0.16);
        color: var(--secondary-text-color);
      }
      .log-level.debug .dot {
        background: var(--cat-other, #9aa0a6);
      }
      .log-level.info {
        background: rgba(42, 120, 214, 0.14);
        color: var(--cat-1, #2a78d6);
      }
      .log-level.info .dot {
        background: var(--cat-1, #2a78d6);
      }
      .log-level.warning {
        background: rgba(250, 178, 25, 0.16);
        color: #7a5200;
      }
      .log-level.warning .dot {
        background: var(--status-warning, #fab219);
      }
      .log-level.error {
        background: rgba(236, 131, 90, 0.18);
        color: var(--status-serious, #ec835a);
      }
      .log-level.error .dot {
        background: var(--status-serious, #ec835a);
      }
      .log-level.critical {
        background: rgba(208, 59, 59, 0.18);
        color: var(--status-critical, #d03b3b);
      }
      .log-level.critical .dot {
        background: var(--status-critical, #d03b3b);
      }
      :host(.dark) .log-level.warning {
        color: var(--status-warning, #fab219);
      }
      .fault-log pre,
      .rawlog {
        white-space: pre-wrap;
        font-size: 11.5px;
        background: rgba(var(--rgb-primary-text-color, 0, 0, 0), 0.04);
        padding: 10px;
        border-radius: 6px;
        margin: 0;
        max-height: 400px;
        overflow-y: auto;
      }
      .rawlog {
        max-height: 600px;
        font-family: var(--code-font-family, monospace);
      }
    `],Ae.LOG_SORT={time:t=>t.first_occurred,level:t=>{const e=Se.indexOf(t.level.toUpperCase());return-1===e?null:e},integration:t=>ke(t.name),message:t=>t.message[t.message.length-1],count:t=>t.count},t([ut()],Ae.prototype,"_entries",void 0),t([ut()],Ae.prototype,"_fault",void 0),t([ut()],Ae.prototype,"_loading",void 0),t([ut()],Ae.prototype,"_error",void 0),t([ut()],Ae.prototype,"_domainFilter",void 0),t([ut()],Ae.prototype,"_levelFilter",void 0),t([ut()],Ae.prototype,"_expanded",void 0),t([ut()],Ae.prototype,"_sort",void 0),t([ut()],Ae.prototype,"_targets",void 0),t([ut()],Ae.prototype,"_source",void 0),t([ut()],Ae.prototype,"_containerLog",void 0),t([ut()],Ae.prototype,"_containerLoading",void 0),Ae=xe=t([dt("ha-soc-logs-view")],Ae);let ze=Pe=class extends Ot{constructor(){super(...arguments),this._overview=null,this._loading=!0,this._error=null,this._busyKey=null,this._showIgnored=!1,this._sort=null,this._ignoredSort=null}get viewId(){return"peripherals"}connectedCallback(){super.connectedCallback(),this._load()}async _load(){this._loading=!0,this._error=null;try{this._overview=await zt(this.hass)}catch(t){this._error=t?.message??String(t)}finally{this._loading=!1}}async _onToggleIgnore(t,e,s){this._busyKey=t;try{await((t,e,s,i)=>gt(t,{type:"ha_soc/peripherals/set_ignored",key:e,ignored:s,raw_name:i}))(this.hass,t,e,s),await this._load()}finally{this._busyKey=null}}render(){if(this._loading)return B`<div class="empty">Loading peripherals…</div>`;if(this._error)return B`
        <div class="card" style="border:1px solid var(--error-color,#db4437);">
          <h3>Could not load Local Peripherals</h3>
          <p style="font-size:13px;">${this._error}</p>
          <button class="ha-btn" @click=${()=>this._load()}>Retry</button>
        </div>
      `;const t=this._overview;if(!t||!t.available)return B`
        <div class="card">
          <h3>Local Peripherals</h3>
          <p class="muted" style="font-size:12.5px;">
            Home Assistant's own USB discovery component (<code>usb</code>) isn't
            available — it's part of every default install, so this usually only
            happens if it's been explicitly disabled. This view has nothing to read
            without it.
          </p>
        </div>
      `;const e=t.devices.filter(t=>!t.ignored),s=t.devices.filter(t=>t.ignored),i=[{id:"peripherals",title:"Local Peripherals",hideable:!1,render:()=>B`
      <div class="card">
        <h3>Local Peripherals</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          USB serial devices Home Assistant itself can see — the same discovery data
          core uses to auto-detect a Zigbee/Z-Wave USB stick, so no add-on is involved.
          This only covers serial (<code>/dev/ttyUSB*</code>/<code>/dev/ttyACM*</code>)
          devices, not every USB peripheral. "Assigned integration" is a best-effort
          match against every config entry's stored data — a miss doesn't prove a
          device is unused, only that this couldn't find it.
        </p>
        ${t.devices.length?B`
              <table>
                <thead>
                  <tr>
                    ${Ut("Raw Name","name",this._sort,t=>this._sort=t)}
                    ${Ut("/dev/tty Path","tty",this._sort,t=>this._sort=t)}
                    ${Ut("By-ID Path","by_id",this._sort,t=>this._sort=t)}
                    ${Ut("VID:PID","vidpid",this._sort,t=>this._sort=t)}
                    ${Ut("Serial","serial",this._sort,t=>this._sort=t)}
                    ${Ut("Assigned Integration","integration",this._sort,t=>this._sort=t)}
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  ${Dt(e,this._sort,Pe.DEVICE_SORT).map(t=>B`
                      <tr>
                        <td>${t.raw_name}</td>
                        <td class="muted">${t.tty_path}</td>
                        <td class="muted" style="font-size:12px;word-break:break-all;">
                          ${t.by_id_path??"—"}
                        </td>
                        <td class="muted" style="font-size:12px;">${t.vid}:${t.pid}</td>
                        <td class="muted" style="font-size:12px;">${t.serial_number??"—"}</td>
                        <td>
                          ${t.assigned_integration?B`${t.assigned_integration.title}
                                <span class="muted">(${t.assigned_integration.domain})</span>`:B`<span class="pill medium"><span class="dot"></span>unassigned</span>`}
                        </td>
                        <td>
                          ${t.assigned_integration?W:B`
                                <button
                                  class="ha-btn"
                                  ?disabled=${this._busyKey===t.key}
                                  @click=${()=>this._onToggleIgnore(t.key,!0,t.raw_name)}
                                >
                                  Ignore
                                </button>
                              `}
                        </td>
                      </tr>
                    `)}
                </tbody>
              </table>
            `:B`<div class="empty">
              No USB serial devices detected. If you're expecting one here, confirm
              Home Assistant actually has access to it — automatic on Home Assistant
              OS for devices your system exposes; a Container/Core install needs the
              device passed through explicitly (e.g. Docker's <code>--device</code>).
            </div>`}
      </div>
        `},{id:"ignored_peripherals",title:"Ignored Peripherals",render:()=>s.length?B`
            <div class="card">
              <h3 style="cursor:pointer;" @click=${()=>this._showIgnored=!this._showIgnored}>
                Ignored (${s.length}) ${this._showIgnored?"▲":"▼"}
              </h3>
              ${this._showIgnored?B`
                    <table>
                      <thead>
                        <tr>
                          ${Ut("Raw Name","name",this._ignoredSort,t=>this._ignoredSort=t)}
                          ${Ut("/dev/tty Path","tty",this._ignoredSort,t=>this._ignoredSort=t)}
                          <th></th>
                        </tr>
                      </thead>
                      <tbody>
                        ${Dt(s,this._ignoredSort,Pe.DEVICE_SORT).map(t=>B`
                            <tr class="row-disabled">
                              <td>${t.raw_name}</td>
                              <td class="muted">${t.tty_path}</td>
                              <td>
                                <button
                                  class="ha-btn"
                                  ?disabled=${this._busyKey===t.key}
                                  @click=${()=>this._onToggleIgnore(t.key,!1,t.raw_name)}
                                >
                                  Un-ignore
                                </button>
                              </td>
                            </tr>
                          `)}
                      </tbody>
                    </table>
                  `:W}
            </div>
          `:W}];return this._renderSections(i)}};var Ee;ze.styles=Ft,ze.DEVICE_SORT={name:t=>t.raw_name,tty:t=>t.tty_path,by_id:t=>t.by_id_path,vidpid:t=>`${t.vid}:${t.pid}`,serial:t=>t.serial_number,integration:t=>t.assigned_integration?.title??null},t([ut()],ze.prototype,"_overview",void 0),t([ut()],ze.prototype,"_loading",void 0),t([ut()],ze.prototype,"_error",void 0),t([ut()],ze.prototype,"_busyKey",void 0),t([ut()],ze.prototype,"_showIgnored",void 0),t([ut()],ze.prototype,"_sort",void 0),t([ut()],ze.prototype,"_ignoredSort",void 0),ze=Pe=t([dt("ha-soc-peripherals-view")],ze);const Re={automation:"Automations",script:"Scripts",scene:"Scenes",dashboard:"Views (dashboards)",helper:"Helpers",other:"Other (review manually)"};let Ie=Ee=class extends Ot{constructor(){super(...arguments),this._entities=[],this._oldEntityId="",this._newEntityId="",this._report=null,this._finding=!1,this._applying=!1,this._applyResult=null,this._backupAck=!1,this._applyError=null,this._broken=[],this._brokenLoading=!0,this._brokenError=null,this._brokenFilter=null,this._brokenSort=null,this._isOwner=!1,this._filterSameType=!0}get viewId(){return"entity_remap"}connectedCallback(){super.connectedCallback(),this._load()}async _load(){this._brokenLoading=!0,this._brokenError=null;try{const[e,s,i]=await Promise.all([(t=this.hass,gt(t,{type:"config/entity_registry/list"})),Et(this.hass),Ct(this.hass).catch(()=>({is_owner:!1}))]);this._entities=e,this._broken=s,this._isOwner=!!i.is_owner}catch(t){this._brokenError=t?.message??String(t)}finally{this._brokenLoading=!1}var t}_labelFor(t){const e=this._entities.find(e=>e.entity_id===t),s=e?.name||e?.original_name;return s?`${s} (${t})`:t}async _onFind(){if(this._oldEntityId){this._finding=!0,this._applyResult=null,this._applyError=null;try{this._report=await(t=this.hass,e=this._oldEntityId,gt(t,{type:"ha_soc/entity_remap/find_references",entity_id:e})),this._brokenFilter=this._oldEntityId}finally{this._finding=!1}var t,e}}_onFixBroken(t){this._oldEntityId=t,this._newEntityId="",this._report=null,this._applyResult=null,this._applyError=null,this._onFind()}_selectOld(t){this._oldEntityId=t,this._newEntityId="",this._report=null,this._applyResult=null,this._applyError=null,this.updateComplete.then(()=>{this.renderRoot?.querySelector("#remap-card")?.scrollIntoView({behavior:"smooth",block:"start"})})}_domainOf(t){return t.includes(".")?t.split(".",1)[0]:""}_newEntityOptions(){const t=this._domainOf(this._oldEntityId);return this._filterSameType&&t?this._entities.filter(e=>this._domainOf(e.entity_id)===t):this._entities}_onClearBrokenFilter(){this._brokenFilter=null}_filteredBroken(){return this._brokenFilter?this._broken.filter(t=>t.entity_id===this._brokenFilter):this._broken}async _onApply(){if(this._oldEntityId&&this._newEntityId){this._applying=!0,this._applyError=null;try{const a=await(t=this.hass,e=this._oldEntityId,s=this._newEntityId,i=this._backupAck,gt(t,{type:"ha_soc/entity_remap/apply",old_entity_id:e,new_entity_id:s,backup_acknowledged:i}));this._backupAck=!1,await this._onFind(),this._broken=await Et(this.hass),this._applyResult=a}catch(t){this._applyError=t?.message??t?.code??"Applying the remap failed."}finally{this._applying=!1}var t,e,s,i}}_renderKind(t,e){return e.length?B`
      <div style="margin-bottom:12px;">
        <div style="font-size:12px;font-weight:600;color:var(--secondary-text-color);margin-bottom:4px;">
          ${Re[t]??t} (${e.length})
        </div>
        <table>
          <tbody>
            ${e.map(t=>B`
                <tr>
                  <td>${t.name}</td>
                  <td>
                    <span class="tag ${t.editable?"enforced":"cosmetic"}">
                      ${t.editable?"will fix":"manual review"}
                    </span>
                  </td>
                  <td class="muted" style="font-size:12px;">${t.reason??""}</td>
                </tr>
              `)}
          </tbody>
        </table>
      </div>
    `:W}render(){const t=this._report,e=!!t&&t.editable_count>0&&!!this._newEntityId&&this._newEntityId!==this._oldEntityId&&this._backupAck,s=[{id:"entity_remap",title:"Entity ReMap",hideable:!1,render:()=>B`
      <div class="card" id="remap-card">
        <h3>Entity ReMap</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Home Assistant has no built-in way to do this: renaming or replacing an entity
          only ever touches the entity registry — every automation, script, scene,
          dashboard, and helper that still references the old entity_id keeps that exact
          string and silently breaks. Pick the broken/old entity and its replacement below
          to find every reference and fix the ones that are safely, structurally editable.
          A reference that only exists inside a template (<code>{{ states('...') }}</code>)
          is never rewritten automatically — it's flagged for you to fix by hand instead,
          since a text rewrite there risks corrupting the template or missing a dynamic
          reference.
        </p>

        <div class="toolbar" style="align-items:flex-end;">
          <div>
            <div class="muted" style="font-size:11px;margin-bottom:2px;">Old / broken entity</div>
            <input
              list="ha-soc-remap-old-entities"
              style="width:320px;"
              .value=${this._oldEntityId}
              placeholder="sensor.old_entity_id"
              @change=${t=>this._oldEntityId=t.target.value.trim()}
            />
          </div>
          <div>
            <div class="muted" style="font-size:11px;margin-bottom:2px;">New / replacement entity</div>
            <input
              list="ha-soc-remap-new-entities"
              style="width:320px;"
              .value=${this._newEntityId}
              placeholder="sensor.new_entity_id"
              @change=${t=>this._newEntityId=t.target.value.trim()}
            />
          </div>
          <button class="ha-btn" ?disabled=${!this._oldEntityId||this._finding} @click=${()=>this._onFind()}>
            ${this._finding?"Searching…":"Find references"}
          </button>
          <label
            class="muted"
            style="display:inline-flex;align-items:center;gap:6px;font-size:12.5px;cursor:pointer;"
            title="Only suggest replacement entities in the same domain (binary_sensor, sensor, weather, …) as the old entity"
          >
            <input
              type="checkbox"
              .checked=${this._filterSameType}
              @change=${t=>this._filterSameType=t.target.checked}
            />
            Filter by same Entity Type
          </label>
          <!-- Old/broken entity only offers entities this page already knows are
               referenced-but-missing — picking from the full entity registry made
               no sense here, since a genuinely broken entity isn't in it. -->
          <datalist id="ha-soc-remap-old-entities">
            ${this._broken.map(t=>B`<option value=${t.entity_id}>${this._labelFor(t.entity_id)}</option>`)}
          </datalist>
          <!-- New/replacement entity picks from currently-registered entities,
               constrained to the old entity's domain when the checkbox is on. -->
          <datalist id="ha-soc-remap-new-entities">
            ${this._newEntityOptions().map(t=>B`<option value=${t.entity_id}>${t.name??t.original_name??""}</option>`)}
          </datalist>
        </div>

        ${t?B`
              <div style="margin-top:12px;">
                ${0===t.total_count?B`<div class="empty">No references to ${t.entity_id} found anywhere.</div>`:B`
                      <p class="muted" style="font-size:12.5px;">
                        ${t.total_count} reference(s) found — ${t.editable_count} can be fixed
                        automatically, the rest need a manual look.
                      </p>
                      ${this._renderKind("automation",t.automation)}
                      ${this._renderKind("script",t.script)}
                      ${this._renderKind("scene",t.scene)}
                      ${this._renderKind("dashboard",t.dashboard)}
                      ${this._renderKind("helper",t.helper)}
                      ${this._renderKind("other",t.other)}
                    `}
                ${this._isOwner?B`
                      ${t.editable_count>0?B`
                            <!-- The server refuses the apply without backup_acknowledged, so this
                                 checkbox is the same required gate the firewall card's backup
                                 acknowledgment is, with the consequences spelled out honestly. -->
                            <label
                              style="display:flex;align-items:flex-start;gap:8px;font-size:12.5px;margin-top:12px;cursor:pointer;"
                            >
                              <input
                                type="checkbox"
                                style="margin-top:2px;"
                                .checked=${this._backupAck}
                                @change=${t=>this._backupAck=t.target.checked}
                              />
                              <span>
                                I understand that before their first rewrite,
                                <code>automations.yaml</code>, <code>scripts.yaml</code>, and
                                <code>scenes.yaml</code> are each copied aside as
                                <code>&lt;file&gt;.ha_soc-&lt;timestamp&gt;.bak</code>; that
                                storage-mode dashboards and helper entries get a JSON snapshot of
                                their previous state under <code>.storage/ha_soc_remap/</code>
                                (kept for 30 days) before being rewritten in place; that a YAML
                                file containing <code>!secret</code> or <code>!include</code> is
                                refused entirely and reported as "manual edit required"; that
                                comments and formatting in the YAML files do not survive the
                                rewrite; and that automations, scripts, and scenes reload right
                                after the write.
                              </span>
                            </label>
                          `:W}
                      <button
                        class="ha-btn"
                        style="margin-top:12px;"
                        ?disabled=${!e||this._applying}
                        @click=${()=>this._onApply()}
                      >
                        ${this._applying?"Applying…":`Apply remap (${t.editable_count} reference${1===t.editable_count?"":"s"})`}
                      </button>
                    `:B`
                      <!-- Applying is owner-only server-side (D-23), so a non-owner
                           admin gets the Settings tab's one-line note instead of an
                           apply button that could only ever bounce off the gate. -->
                      <p class="muted" style="font-size:12.5px;margin-top:12px;">
                        Applying a remap is available to the account owner only.
                      </p>
                    `}
              </div>
            `:W}

        ${this._applyError?B`<p style="color:var(--error-color,#db4437);font-size:12.5px;margin-top:10px;">
              Apply failed: ${this._applyError}
            </p>`:W}

        ${this._applyResult?B`
              <div class="card" style="margin-top:12px;background:rgba(67,160,71,0.08);">
                <strong>Applied.</strong> ${Object.entries(this._applyResult.fixed).filter(([,t])=>t>0).map(([t,e])=>`${e} ${Re[t]??t}`).join(", ")||"Nothing needed changing."}
                ${this._applyResult.errors.length?B`<div style="color:var(--error-color);margin-top:6px;">
                      ${this._applyResult.errors.length} error(s): ${this._applyResult.errors.join("; ")}
                    </div>`:W}
                ${this._applyResult.backups?.length?B`<div class="muted" style="font-size:12px;margin-top:6px;">
                      Backups written before the rewrite:
                      ${this._applyResult.backups.map(t=>B`<div><code>${t}</code></div>`)}
                    </div>`:W}
              </div>
            `:W}
      </div>
        `},{id:"broken_references",title:"Entities referenced but not found",render:()=>B`
      <div class="card">
        <h3>
          Entities referenced but not found (${this._filteredBroken().length}${this._brokenFilter?B` of ${this._broken.length}`:W})
        </h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          A proactive sweep of every automation, script, scene, and structured helper —
          any entity_id they reference that doesn't correspond to a known entity right now.
          Dashboards aren't swept here (there's no equivalent core-provided index to walk
          cheaply); use the search above for a specific entity_id to also cover those.
        </p>
        ${this._brokenFilter?B`
              <div class="toolbar" style="margin-bottom:8px;">
                <span class="muted" style="font-size:12px;">
                  Filtered to <code>${this._brokenFilter}</code>
                </span>
                <button class="ha-btn" @click=${()=>this._onClearBrokenFilter()}>Clear filter</button>
              </div>
            `:W}
        ${this._brokenLoading?B`<div class="empty">Loading…</div>`:this._brokenError?B`
                <div style="border:1px solid var(--error-color,#db4437);border-radius:6px;padding:10px 12px;">
                  <p style="font-size:13px;margin:0 0 8px;">${this._brokenError}</p>
                  <button class="ha-btn" @click=${()=>this._load()}>Retry</button>
                </div>
              `:this._broken.length?this._filteredBroken().length?B`
                <table>
                  <thead>
                    <tr>
                      ${Ut("Entity ID","entity_id",this._brokenSort,t=>this._brokenSort=t)}
                      ${Ut("Referenced by","referenced_by",this._brokenSort,t=>this._brokenSort=t)}
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    ${Dt(this._filteredBroken(),this._brokenSort,Ee.BROKEN_SORT).map(t=>B`
                        <tr>
                          <td>
                            <code
                              style="cursor:pointer;color:var(--primary-color);"
                              title="Select as the Old / broken entity"
                              @click=${()=>this._selectOld(t.entity_id)}
                              >${t.entity_id}</code
                            >
                          </td>
                          <td class="muted" style="font-size:12px;">
                            ${t.referenced_by.map(t=>`${t.name} (${t.kind})`).join(", ")}
                          </td>
                          <td>
                            <button class="ha-btn" @click=${()=>this._onFixBroken(t.entity_id)}>Fix…</button>
                          </td>
                        </tr>
                      `)}
                  </tbody>
                </table>
              `:B`<div class="empty">No broken reference matches <code>${this._brokenFilter}</code>.</div>`:B`<div class="empty">Nothing found — no dangling entity references detected.</div>`}
      </div>
        `}];return this._renderSections(s)}};var Fe;Ie.styles=Ft,Ie.BROKEN_SORT={entity_id:t=>t.entity_id,referenced_by:t=>t.referenced_by[0]?.name??null},t([ut()],Ie.prototype,"_entities",void 0),t([ut()],Ie.prototype,"_oldEntityId",void 0),t([ut()],Ie.prototype,"_newEntityId",void 0),t([ut()],Ie.prototype,"_report",void 0),t([ut()],Ie.prototype,"_finding",void 0),t([ut()],Ie.prototype,"_applying",void 0),t([ut()],Ie.prototype,"_applyResult",void 0),t([ut()],Ie.prototype,"_backupAck",void 0),t([ut()],Ie.prototype,"_applyError",void 0),t([ut()],Ie.prototype,"_broken",void 0),t([ut()],Ie.prototype,"_brokenLoading",void 0),t([ut()],Ie.prototype,"_brokenError",void 0),t([ut()],Ie.prototype,"_brokenFilter",void 0),t([ut()],Ie.prototype,"_brokenSort",void 0),t([ut()],Ie.prototype,"_isOwner",void 0),t([ut()],Ie.prototype,"_filterSameType",void 0),Ie=Ee=t([dt("ha-soc-entity-remap-view")],Ie);const Te={core:"Core",hacs:"HACS",custom:"Custom"},Ne={core:"good",hacs:"medium",custom:"high"},Le={core:0,hacs:1,custom:2},Oe={custom_repo:"Custom repo",custom_source_list:"Custom source-list"};let De=Fe=class extends Ot{constructor(){super(...arguments),this._overview=null,this._loading=!0,this._error=null,this._refreshing=!1,this._search="",this._tierFilter="all",this._limit=25,this._intSort=null,this._containerSort=null,this._containers=null,this._containersLoading=!0,this._watchdog=null,this._editSlug=null,this._wdError=null}get viewId(){return"integration_security"}connectedCallback(){super.connectedCallback(),this._load(),this._loadContainers(),this._loadWatchdog()}async _loadWatchdog(){try{this._watchdog=await(t=this.hass,gt(t,{type:"ha_soc/watchdog/status"}))}catch{this._watchdog=null}var t}async _setWatchdog(t){this._wdError=null;try{this._watchdog=await((t,e)=>gt(t,{type:"ha_soc/watchdog/set",...e}))(this.hass,t)}catch(t){this._wdError=t&&"object"==typeof t&&"code"in t&&"unauthorized"===t.code?"Watchdog and cap configuration are available to the account owner only.":`Could not save: ${t instanceof Error?t.message:JSON.stringify(t)}`}}async _load(){this._loading=!0,this._error=null;try{this._overview=await(t=this.hass,gt(t,{type:"ha_soc/integration_security/list"}))}catch(t){this._error=t?.message??String(t)}finally{this._loading=!1}var t}async _loadContainers(){this._containersLoading=!0;try{this._containers=await(t=this.hass,gt(t,{type:"ha_soc/containers/resources"}))}catch{this._containers=null}finally{this._containersLoading=!1}var t}async _onRefresh(){this._refreshing=!0;try{await(t=this.hass,gt(t,{type:"ha_soc/integration_security/refresh"})),await this._load()}finally{this._refreshing=!1}var t}_filtered(){const t=this._overview?.integrations??[],e=this._search.trim().toLowerCase(),s=t.filter(t=>"all"===this._tierFilter||t.tier===this._tierFilter).filter(t=>!e||t.name.toLowerCase().includes(e)||t.domain.toLowerCase().includes(e));return this._intSort?Dt(s,this._intSort,Fe.INTEGRATION_SORT):s.sort((t,e)=>t.name.localeCompare(e.name))}render(){if(this._loading)return B`<div class="empty">Loading integrations…</div>`;if(this._error||!this._overview)return B`
        <div class="card" style="border:1px solid var(--error-color,#db4437);">
          <h3>Could not load Integration Security</h3>
          <p style="font-size:13px;">${this._error??"The server returned no data."}</p>
          <button class="ha-btn" @click=${()=>this._load()}>Retry</button>
        </div>
      `;const t=this._overview,e=this._filtered(),s=e.slice(0,this._limit),i=this._intSort,a=t=>{this._intSort=t,this._limit=25},r=[{id:"integration_security",title:"Integration Security",hideable:!1,render:()=>B`
      <div class="card">
        <h3>Integration Security</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          <span class="tag cosmetic">provenance, not safety</span> This measures how much is
          known about where each integration's code came from and how it's maintained — it
          is <strong>not</strong> a verdict that the code is safe to run. Home Assistant
          runs integrations in-process with no sandbox; a high-provenance integration can
          still do anything a low-provenance one can.
        </p>

        <div class="toolbar" style="margin-top:12px;">
          <div class="pill" style="--tone-unused:0">
            <span class="dot" style="background:var(--success-color,#43a047);"></span>
            Core ${t.tier_counts.core}
          </div>
          <div class="pill">
            <span class="dot" style="background:var(--warning-color,#ffa600);"></span>
            HACS ${t.tier_counts.hacs}
          </div>
          <div class="pill">
            <span class="dot" style="background:var(--error-color,#db4437);"></span>
            Custom ${t.tier_counts.custom}
          </div>
          <span class="spacer"></span>
          <button class="ha-btn" ?disabled=${this._refreshing||!t.github_configured} @click=${this._onRefresh}>
            ${this._refreshing?"Refreshing…":"Refresh GitHub signals"}
          </button>
        </div>

        ${t.github_configured?t.refreshed_at?B`<p class="muted" style="font-size:12px;margin:0 0 4px;">
                GitHub signals last refreshed ${new Date(t.refreshed_at).toLocaleString()}.
              </p>`:W:B`<p class="muted" style="font-size:12px;margin:0 0 4px;">
              GitHub-derived signals are <strong>not collected</strong> — set a GitHub token
              in the owner-only Settings tab to enable them.
            </p>`}
        ${t.hacs_installed&&!t.hacs_source_introspectable?B`<p class="muted" style="font-size:12px;margin:0;">
              HACS is installed but its per-repository source (default store vs. custom
              repo) isn't readable here, so HACS-managed content is shown as
              <em>Custom</em> and source flags are unverified.
            </p>`:W}
      </div>

      <div class="card">
        <div class="toolbar">
          <input
            type="text"
            placeholder="Search integrations…"
            .value=${this._search}
            @input=${t=>{this._search=t.target.value,this._limit=25}}
            style="flex:1 1 220px;"
          />
          <select
            .value=${this._tierFilter}
            @change=${t=>{this._tierFilter=t.target.value,this._limit=25}}
          >
            <option value="all">All tiers</option>
            <option value="core">Core</option>
            <option value="hacs">HACS</option>
            <option value="custom">Custom</option>
          </select>
        </div>

        ${e.length?B`
              <div style="overflow-x:auto;">
                <table>
                  <thead>
                    <tr>
                      ${Ut("Integration","name",i,a)}
                      ${Ut("Source","tier",i,a)}
                      ${Ut("Quality","quality",i,a)}
                      ${Ut("License","license",i,a)}
                      ${Ut("Scanner","scanner",i,a)}
                      ${Ut("Signed","signed",i,a)}
                      ${Ut("Release","release",i,a)}
                      ${Ut("Stars","stars",i,a)}
                      ${Ut("Last push","pushed",i,a)}
                    </tr>
                  </thead>
                  <tbody>
                    ${s.map(t=>this._renderRow(t))}
                  </tbody>
                </table>
              </div>
              ${e.length>this._limit?B`
                    <div class="toolbar" style="justify-content:center;margin-top:12px;">
                      <button class="ha-btn" @click=${()=>this._limit+=25}>
                        Show more (${e.length-this._limit} more)
                      </button>
                    </div>
                  `:W}
              <p class="muted" style="font-size:11.5px;margin-top:8px;">
                Showing ${Math.min(this._limit,e.length)} of ${e.length}.
              </p>
            `:B`<div class="empty">No integrations match.</div>`}
      </div>
        `},{id:"container_resources",title:"Container Resource Usage",render:()=>this._renderContainers()}];return this._renderSections(r)}_notCollected(){return B`<span class="muted" title="No GitHub token, or no repo URL discovered">—</span>`}_fmtBytes(t){if(null==t)return"—";if(t<1024)return`${t} B`;const e=["KB","MB","GB","TB"];let s=t/1024,i=0;for(;s>=1024&&i<e.length-1;)s/=1024,i++;return`${s.toFixed(s>=100?0:1)} ${e[i]}`}_pctCell(t,e){if(null==t)return B`<span class="muted">—</span>`;return B`<span style="font-weight:600;color:${e?"var(--status-critical)":t>=60?"var(--status-warning)":"inherit"};font-variant-numeric:tabular-nums;"
      >${t.toFixed(1)}%</span
    >`}_renderContainers(){const t=this._containers,e=this._containerSort,s=t=>this._containerSort=t;return B`
      <div class="card">
        <div class="toolbar">
          <h3 style="margin:0;flex:1;">Container Resource Usage</h3>
          <button class="ha-btn" ?disabled=${this._containersLoading} @click=${()=>this._loadContainers()}>
            ${this._containersLoading?"Refreshing…":"Refresh"}
          </button>
        </div>
        <p class="muted" style="margin-top:-4px;font-size:12.5px;">
          Live per-container CPU and memory for every add-on plus Home Assistant Core and
          the Supervisor. A container sitting near its <strong>memory limit</strong> (or
          pinning CPU) is the usual signal for the one that's OOM-killing / restart-looping
          and dragging the host down — those float to the top and are flagged.
        </p>
        ${this._renderWatchdogBar()}
        ${this._containersLoading&&!t?B`<div class="empty">Loading container stats…</div>`:t&&t.available?t.containers.length?B`
                  <div style="overflow-x:auto;">
                    <table>
                      <thead>
                        <tr>
                          ${Ut("Container","name",e,s)}
                          ${Ut("State","state",e,s)}
                          ${Ut("CPU","cpu",e,s,{numeric:!0})}
                          ${Ut("Memory","memory",e,s,{numeric:!0})}
                          ${Ut("Used / Limit","usage",e,s)}
                          ${Ut("Net ↓/↑","net",e,s)}
                          ${Ut("Disk R/W","disk",e,s)}
                          ${Ut("Flags","flags",e,s)}
                          <th>Watchdog / Cap</th>
                        </tr>
                      </thead>
                      <tbody>
                        ${Dt(t.containers,e,Fe.CONTAINER_SORT).map(t=>this._renderContainerRow(t))}
                      </tbody>
                    </table>
                  </div>
                  ${this._renderEditor()}
                  ${this._renderWatchdogActivity()}
                  <p class="muted" style="font-size:11.5px;margin-top:8px;">
                    Updated ${new Date(t.generated_at).toLocaleTimeString()}. CPU/memory are
                    an instantaneous sample — click Refresh to re-poll.
                  </p>
                `:B`<div class="empty">No containers reported.</div>`:B`<div class="empty">
                ${"not_supervisor"===t?.reason?"Per-container stats need a Supervisor-based install (Home Assistant OS or Supervised). This install doesn't run under Supervisor, so there are no add-on containers to measure.":"Container stats aren't available right now."}
              </div>`}
      </div>
    `}_renderWatchdogBar(){const t=this._watchdog;if(!t)return W;const e=t.config;return B`
      <div
        style="border:1px solid var(--divider-color);border-radius:10px;padding:10px 14px;margin-bottom:12px;"
      >
        <div class="toolbar" style="margin-bottom:${e.enabled?"8px":"0"};">
          <label style="display:inline-flex;align-items:center;gap:8px;font-weight:600;font-size:13.5px;cursor:pointer;">
            <input
              type="checkbox"
              .checked=${e.enabled}
              @change=${t=>this._setWatchdog({enabled:t.target.checked})}
            />
            Resource Watchdog
          </label>
          <span class="muted" style="font-size:12px;">
            ${e.enabled?`sampling every ${e.interval_seconds}s — acts after ${e.sustained_samples} sustained breaches`:"off — no automatic detection or action (owner-only setting)"}
          </span>
        </div>
        ${e.enabled?B`
              <div class="toolbar" style="gap:14px;margin-bottom:0;">
                <label class="muted" style="font-size:12px;display:inline-flex;align-items:center;gap:6px;">
                  CPU ≥
                  <input type="number" min="10" max="100" style="width:64px;" .value=${String(e.default_cpu_percent)}
                    @change=${t=>this._setWatchdog({default_cpu_percent:Number(t.target.value)})} />%
                </label>
                <label class="muted" style="font-size:12px;display:inline-flex;align-items:center;gap:6px;">
                  Memory ≥
                  <input type="number" min="10" max="100" style="width:64px;" .value=${String(e.default_memory_percent)}
                    @change=${t=>this._setWatchdog({default_memory_percent:Number(t.target.value)})} />%
                </label>
                <label class="muted" style="font-size:12px;display:inline-flex;align-items:center;gap:6px;">
                  Default action
                  <select .value=${e.default_action}
                    @change=${t=>this._setWatchdog({default_action:t.target.value})}>
                    <option value="alert" ?selected=${"alert"===e.default_action}>Alert only</option>
                    <option value="restart" ?selected=${"restart"===e.default_action}>Restart add-on</option>
                    <option value="stop" ?selected=${"stop"===e.default_action}>Stop add-on</option>
                  </select>
                </label>
                <label class="muted" style="font-size:12px;display:inline-flex;align-items:center;gap:6px;">
                  Sustained samples
                  <input type="number" min="1" max="30" style="width:56px;" .value=${String(e.sustained_samples)}
                    @change=${t=>this._setWatchdog({sustained_samples:Number(t.target.value)})} />
                </label>
              </div>
              <p class="muted" style="font-size:11.5px;margin:6px 0 0;">
                Home Assistant Core and the Supervisor are always alert-only — the watchdog
                never auto-restarts them, whatever the default. After 3 enforcement actions
                on one container within an hour it downgrades that container to alert-only
                (a restart loop needs a human, not more restarts).
              </p>
            `:W}
        ${this._wdError?B`<p style="color:var(--error-color,#db4437);font-size:12.5px;margin:6px 0 0;">${this._wdError}</p>`:W}
      </div>
    `}_wdCell(t){const e=this._watchdog;if(!e)return B`<span class="muted">—</span>`;const s=e.config,i=s.overrides?.[t.slug]??{},a=i.cpu_percent??s.default_cpu_percent,r=i.memory_percent??s.default_memory_percent,o="addon"===t.kind?i.action??s.default_action:"alert",n=s.hard_limits?.[t.slug],l=e.hard_limit_state?.[t.slug],d=n?l?B`<span
            class="pill ${"applied"===l.status?"good":"high"}"
            title=${l.detail??l.status}
            ><span class="dot"></span>cap ${l.status}</span
          >`:B`<span class="pill medium" title="Configured; waiting for the Probe to apply"
            ><span class="dot"></span>cap pending</span
          >`:W;return B`
      <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;">
        ${s.enabled&&!1!==i.enabled?B`<span class="muted" style="font-size:11px;" title="Thresholds → action">
              ${a}%/${r}% → ${o}
            </span>`:B`<span class="muted" style="font-size:11px;">off</span>`}
        ${d}
        <button
          class="ha-btn"
          style="padding:2px 8px;font-size:11.5px;"
          @click=${()=>this._editSlug=this._editSlug===t.slug?null:t.slug}
        >
          ${this._editSlug===t.slug?"Close":"Edit"}
        </button>
      </div>
    `}_renderEditor(){const t=this._editSlug,e=this._watchdog,s=this._containers;if(!t||!e||!s)return W;const i=s.containers.find(e=>e.slug===t);if(!i)return W;const a=e.config.overrides?.[t]??{},r=e.config.hard_limits?.[t]??{memory_mb:null,cpus:null},o="addon"===i.kind;return B`
      <div
        style="border:1px solid var(--primary-color);border-radius:10px;padding:12px 14px;margin-top:10px;"
      >
        <div style="font-weight:600;font-size:13.5px;margin-bottom:8px;">
          ${i.name} <span class="muted" style="font-weight:400;">— per-container watchdog & cap</span>
        </div>
        <div class="toolbar" style="gap:14px;">
          <label class="muted" style="font-size:12px;display:inline-flex;align-items:center;gap:6px;">
            CPU ≥
            <input type="number" min="10" max="100" style="width:64px;"
              placeholder=${String(e.config.default_cpu_percent)}
              .value=${null!=a.cpu_percent?String(a.cpu_percent):""}
              @change=${e=>{const s=e.target.value;this._setWatchdog({override:{slug:t,cpu_percent:s?Number(s):null}})}} />%
          </label>
          <label class="muted" style="font-size:12px;display:inline-flex;align-items:center;gap:6px;">
            Memory ≥
            <input type="number" min="10" max="100" style="width:64px;"
              placeholder=${String(e.config.default_memory_percent)}
              .value=${null!=a.memory_percent?String(a.memory_percent):""}
              @change=${e=>{const s=e.target.value;this._setWatchdog({override:{slug:t,memory_percent:s?Number(s):null}})}} />%
          </label>
          ${o?B`
                <label class="muted" style="font-size:12px;display:inline-flex;align-items:center;gap:6px;">
                  Action
                  <select .value=${a.action??e.config.default_action}
                    @change=${e=>this._setWatchdog({override:{slug:t,action:e.target.value}})}>
                    <option value="alert" ?selected=${"alert"===(a.action??e.config.default_action)}>Alert only</option>
                    <option value="restart" ?selected=${"restart"===(a.action??e.config.default_action)}>Restart</option>
                    <option value="stop" ?selected=${"stop"===(a.action??e.config.default_action)}>Stop</option>
                  </select>
                </label>
              `:B`<span class="muted" style="font-size:12px;">action: alert only (never auto-restarted)</span>`}
          <button class="ha-btn" style="font-size:11.5px;" @click=${()=>this._setWatchdog({override:{slug:t,clear:!0}})}>
            Reset to defaults
          </button>
        </div>
        ${o?B`
              <div class="toolbar" style="gap:14px;margin-top:8px;margin-bottom:0;">
                <span style="font-size:12.5px;font-weight:600;">Hard cap (Docker):</span>
                <label class="muted" style="font-size:12px;display:inline-flex;align-items:center;gap:6px;">
                  Memory
                  <input type="number" min="64" step="64" style="width:84px;" placeholder="unlimited"
                    .value=${null!=r.memory_mb?String(r.memory_mb):""}
                    @change=${e=>{const s=e.target.value;this._setWatchdog({hard_limit:{slug:t,memory_mb:s?Number(s):null,cpus:r.cpus}})}} /> MB
                </label>
                <label class="muted" style="font-size:12px;display:inline-flex;align-items:center;gap:6px;">
                  CPUs
                  <input type="number" min="0.1" step="0.1" style="width:70px;" placeholder="unlimited"
                    .value=${null!=r.cpus?String(r.cpus):""}
                    @change=${e=>{const s=e.target.value;this._setWatchdog({hard_limit:{slug:t,memory_mb:r.memory_mb,cpus:s?Number(s):null}})}} />
                </label>
                <button class="ha-btn" style="font-size:11.5px;"
                  @click=${()=>this._setWatchdog({hard_limit:{slug:t,memory_mb:null,cpus:null}})}>
                  Remove cap
                </button>
              </div>
              <p class="muted" style="font-size:11.5px;margin:6px 0 0;">
                ⚠ Hard caps are real Docker limits applied by the HA SOC Probe add-on. They
                require the Probe's <strong>Protection Mode to be disabled</strong> — a
                root-equivalent grant to that add-on (its security rating drops
                accordingly) — and are re-applied automatically every ~60s so they survive
                Supervisor recreating the container on updates. A memory cap means the
                kernel OOM-kills the add-on's process when it exceeds the cap — Supervisor's
                own add-on watchdog then restarts it if enabled.
              </p>
            `:W}
      </div>
    `}_renderWatchdogActivity(){const t=this._watchdog;if(!t)return W;const e=Object.entries(t.containers).filter(([,t])=>t.last_outcome).map(([t,e])=>({slug:t,text:e.last_outcome}));return e.length?B`
      <div style="margin-top:10px;">
        <div style="font-size:12px;font-weight:600;color:var(--secondary-text-color);margin-bottom:4px;">
          RECENT WATCHDOG ACTIVITY
        </div>
        ${e.map(t=>B`
            <div class="muted" style="font-size:12px;font-family:var(--code-font-family,monospace);">
              ${t.slug}: ${t.text}
            </div>
          `)}
      </div>
    `:W}_renderContainerRow(t){const e=t.flags.includes("high_memory"),s=t.flags.includes("high_cpu"),i="addon"===t.kind?"Add-on":"core"===t.kind?"Core":"Supervisor";return B`
      <tr>
        <td>
          <div style="font-weight:600;">${t.name}</div>
          <div class="muted" style="font-size:11.5px;">${i}${t.slug?` · ${t.slug}`:""}</div>
        </td>
        <td>
          ${"started"===t.state||"addon"!==t.kind?B`<span class="muted">running</span>`:B`<span class="pill high"><span class="dot"></span>${t.state??"stopped"}</span>`}
        </td>
        <td class="num">${this._pctCell(t.cpu_percent,s)}</td>
        <td class="num">${this._pctCell(t.memory_percent,e)}</td>
        <td class="muted" style="font-size:12px;">
          ${this._fmtBytes(t.memory_usage)} / ${this._fmtBytes(t.memory_limit)}
        </td>
        <td class="muted" style="font-size:12px;">
          ${this._fmtBytes(t.network_rx)} / ${this._fmtBytes(t.network_tx)}
        </td>
        <td class="muted" style="font-size:12px;">
          ${this._fmtBytes(t.blk_read)} / ${this._fmtBytes(t.blk_write)}
        </td>
        <td>
          ${t.flags.length?B`<div class="chips">
                ${t.flags.map(t=>B`<span class="pill high"><span class="dot"></span>${"high_memory"===t?"high memory":"high_cpu"===t?"high CPU":t.replace("_"," ")}</span>`)}
              </div>`:B`<span class="muted">—</span>`}
        </td>
        <td>${this._wdCell(t)}</td>
      </tr>
    `}_renderRow(t){const e=t.github;return B`
      <tr>
        <td>
          <div style="font-weight:600;">${t.name}</div>
          <div class="muted" style="font-size:11.5px;">
            ${t.domain}${t.version?B` · v${t.version}`:""}
          </div>
          ${t.flags.length?B`<div class="chips" style="margin-top:3px;">
                ${t.flags.map(t=>B`<span class="pill high"><span class="dot"></span>${Oe[t]??t}</span>`)}
              </div>`:W}
        </td>
        <td>
          <span class="pill ${Ne[t.tier]}"><span class="dot"></span>${Te[t.tier]}</span>
        </td>
        <td class="muted">${t.quality_scale??"—"}</td>
        <td>
          ${null===t.license_present?B`<span class="muted">—</span>`:t.license_present?B`<span class="muted" title="License file present">yes</span>`:B`<span class="pill medium" title="No license file found"><span class="dot"></span>none</span>`}
        </td>
        <td>
          ${t.scanner_findings>0?B`<span class="pill high"><span class="dot"></span>${t.scanner_findings}</span>`:B`<span class="muted">0</span>`}
        </td>
        <td>
          ${e?null===e.commit_verified?B`<span class="muted">?</span>`:e.commit_verified?B`<span class="pill good" title="Default-branch head commit is signed/verified"
                    ><span class="dot"></span>signed</span
                  >`:B`<span class="muted" title="No verified signature on the head commit">unsigned</span>`:this._notCollected()}
        </td>
        <td>
          ${e?e.archived?B`<span class="pill high" title="Repository is archived"><span class="dot"></span>archived</span>`:null===e.has_release?B`<span class="muted">?</span>`:e.has_release?B`<span class="muted" title=${e.latest_release_tag??""}>tagged</span>`:B`<span class="pill medium" title="No published release — installs branch HEAD"
                      ><span class="dot"></span>branch</span
                    >`:this._notCollected()}
        </td>
        <td class="muted">${e?e.stars??"—":this._notCollected()}</td>
        <td class="muted" style="font-size:11.5px;">
          ${e?e.pushed_at?new Date(e.pushed_at).toLocaleDateString():"—":this._notCollected()}
        </td>
      </tr>
    `}};De.styles=Ft,De.INTEGRATION_SORT={name:t=>t.name,tier:t=>Le[t.tier],quality:t=>t.quality_scale,license:t=>t.license_present,scanner:t=>t.scanner_findings,signed:t=>t.github?.commit_verified??null,release:t=>{const e=t.github;return e?e.archived?2:null===e.has_release?null:e.has_release?0:1:null},stars:t=>t.github?.stars??null,pushed:t=>t.github?.pushed_at??null},De.CONTAINER_SORT={name:t=>t.name,state:t=>"started"===t.state||"addon"!==t.kind?"running":t.state??"stopped",cpu:t=>t.cpu_percent,memory:t=>t.memory_percent,usage:t=>t.memory_usage,net:t=>null==t.network_rx&&null==t.network_tx?null:(t.network_rx??0)+(t.network_tx??0),disk:t=>null==t.blk_read&&null==t.blk_write?null:(t.blk_read??0)+(t.blk_write??0),flags:t=>t.flags.length},t([ut()],De.prototype,"_overview",void 0),t([ut()],De.prototype,"_loading",void 0),t([ut()],De.prototype,"_error",void 0),t([ut()],De.prototype,"_refreshing",void 0),t([ut()],De.prototype,"_search",void 0),t([ut()],De.prototype,"_tierFilter",void 0),t([ut()],De.prototype,"_limit",void 0),t([ut()],De.prototype,"_intSort",void 0),t([ut()],De.prototype,"_containerSort",void 0),t([ut()],De.prototype,"_containers",void 0),t([ut()],De.prototype,"_containersLoading",void 0),t([ut()],De.prototype,"_watchdog",void 0),t([ut()],De.prototype,"_editSlug",void 0),t([ut()],De.prototype,"_wdError",void 0),De=Fe=t([dt("ha-soc-integration-security-view")],De);const Ue=1048576,Me=[{domain:"lock",label:"Lock entities (any integration)"},{domain:"siren",label:"Siren entities (any integration)"},{domain:"valve",label:"Valve entities (any integration)"}],He=[{domain:"kidde_homesafe",label:"Kidde HomeSafe"},{domain:"elkm1",label:"Elk-M1 Security"},{domain:"unifiprotect",label:"UniFi Protect"},{domain:"keymaster",label:"Keymaster"},{domain:"emporia_vue",label:"Emporia Vue"}],Ve={brute_force_ip:"Brute force (per source IP)",success_after_failures:"Success after failed logins",new_ip_login:"Login from a new network",off_hours_anomaly:"Off-hours activity burst",dormant_revival:"Dormant account revival",mass_entity_burst:"Mass entity control burst",token_minting_anomaly:"Token minting anomaly",disabled_user_activity:"Disabled-user activity",privilege_escalation:"Privilege escalation"};let Be=class extends nt{constructor(){super(...arguments),this._settings=null,this._security=null,this._thresholds=null,this._loading=!0,this._error=null}connectedCallback(){super.connectedCallback(),this._load()}async _load(){this._loading=!0,this._error=null;try{this._settings=await(t=this.hass,gt(t,{type:"ha_soc/settings/get"}));try{this._security=await Rt(this.hass)}catch{this._security=null}try{this._thresholds=await bt(this.hass)}catch{this._thresholds=null}}catch(t){this._error=t?.message??String(t)}finally{this._loading=!1}var t}async _updateThreshold(t,e,s){await It(this.hass,{detection_thresholds:{[t]:{[e]:s}}}),this._thresholds=await bt(this.hass)}async _resetThresholds(){var t;this._thresholds=await(t=this.hass,gt(t,{type:"ha_soc/detections/thresholds_reset"}).then(t=>t.rules))}async _update(t,e){if(!this._settings)return;const s=this._settings;this._settings={...this._settings,[t]:e};try{this._settings=await It(this.hass,{[t]:e})}catch(t){throw this._settings=s,t}}_updateSecuritySource(t,e){this._settings&&this._update("security_sources_enabled",{...this._settings.security_sources_enabled,[t]:e})}_renderSecretField(t,e,s){return B`
      <label class="settings-row">
        <span>${t}</span>
        <input
          type="password"
          placeholder=${s?"configured — type to replace":"unset"}
          @change=${t=>{const s=t.target.value;this._update(e,s||null)}}
        />
      </label>
    `}_renderIntegrationRow(t,e){const s=this._settings,i=this._security?.integrations.filter(e=>e.domain===t)??[],a=i.some(t=>t.installed),r=i.some(t=>t.installed&&"loaded"!==t.state),o=i.find(t=>t.installed)?.entry_id??null,n=a?r?i.find(t=>"loaded"!==t.state).state:"loaded":"not installed";return B`
      <div class="settings-row">
        <span>${e}</span>
        <span
          class="muted ${a&&o?"clickable":""}"
          style="font-size:12px;${r?"color:var(--error-color,#db4437);":""}"
          title=${a&&o?"View in Home Assistant's Devices page":""}
          @click=${()=>a&&o&&se(ie(o))}
          >${n}</span
        >
        <input
          type="checkbox"
          .checked=${s.security_sources_enabled?.[t]??!0}
          @change=${e=>this._updateSecuritySource(t,e.target.checked)}
        />
      </div>
    `}_renderThresholdsCard(t){return B`
      <div class="card">
        <h3>Detection Thresholds</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Every detection rule's tunable parameters, each accepted only within the
          range shown. The secure defaults are the most sensitive values that do not
          alert on ordinary same-network activity - they miss the fewest attacks, at
          the cost of more alerts. Changes apply from the next analysis pass and are
          audited with a per-field diff.
        </p>
        <label class="settings-row">
          <span>
            Evidence retention (days)
            <span class="muted" style="display:block;font-size:11.5px;"
              >Resolved detections and resolved/dismissed findings older than this are
              pruned; open and acknowledged items never expire.</span
            >
          </span>
          <input
            type="number"
            min="30"
            max="3650"
            .value=${String(t.evidence_retention_days)}
            @change=${t=>this._update("evidence_retention_days",Number(t.target.value))}
          />
        </label>
        ${this._thresholds?Object.entries(this._thresholds).map(([t,e])=>B`
                <h4
                  style="margin:16px 0 4px;font-size:12px;text-transform:uppercase;letter-spacing:0.03em;color:var(--secondary-text-color);"
                >
                  ${Ve[t]??t}
                </h4>
                ${Object.entries(e).map(([e,s])=>"bool"===s.type?B`
                        <label class="settings-row">
                          <span>
                            ${e}
                            <span class="muted" style="display:block;font-size:11.5px;"
                              >secure default: ${s.default?"on":"off"}</span
                            >
                          </span>
                          <input
                            type="checkbox"
                            .checked=${Boolean(s.value)}
                            @change=${s=>this._updateThreshold(t,e,s.target.checked)}
                          />
                        </label>
                      `:B`
                        <label class="settings-row">
                          <span>
                            ${e}
                            <span class="muted" style="display:block;font-size:11.5px;"
                              >${s.min} to ${s.max}, secure default ${s.default}</span
                            >
                          </span>
                          <input
                            type="number"
                            min=${String(s.min)}
                            max=${String(s.max)}
                            step=${"float"===s.type?"any":"1"}
                            .value=${String(s.value)}
                            @change=${s=>this._updateThreshold(t,e,Number(s.target.value))}
                          />
                        </label>
                      `)}
              `):B`<p class="muted" style="font-size:12.5px;">Could not load the threshold table.</p>`}
        <div class="toolbar" style="margin-top:12px;">
          <span class="spacer"></span>
          <button class="ha-btn" @click=${this._resetThresholds}>Reset to secure defaults</button>
        </div>
      </div>
    `}render(){if(this._loading)return B`<div class="empty">Loading settings…</div>`;if(this._error||!this._settings)return B`
        <div class="card" style="border:1px solid var(--error-color,#db4437);">
          <h3>Could not load Settings</h3>
          <p style="font-size:13px;">${this._error??"The server returned no settings."}</p>
          <button class="ha-btn" @click=${()=>this._load()}>Retry</button>
        </div>
      `;const t=this._settings;return B`
      ${t.github_token_set?"":B`
            <div
              style="background:#fdf6d8;color:#6b5300;border:1px solid #e8d071;border-radius:8px;padding:12px 16px;margin-bottom:16px;font-size:13.5px;line-height:1.5;"
            >
              <strong>No GitHub API key configured.</strong> The Integration Security tab
              can still classify every integration and run local checks, but the
              GitHub-derived provenance signals — release vs. branch, identity assurance,
              maintenance recency, popularity, and archived status — stay
              <em>“not collected”</em> until a token is set below. A token also raises
              GitHub's rate limit from 60 to 5,000 requests/hour.
            </div>
          `}

      <div class="card">
        <h3>Access Control</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          <span class="tag enforced">enforced</span> Checked server-side on every
          <code>ha_soc/*</code> command, not just on whether the panel is visible in the
          sidebar — a locked-out admin still sees the SOC panel entry (Home Assistant's
          sidebar has no finer-grained hook than admin/non-admin) but every request it
          makes is rejected until this is opened up.
        </p>
        <label class="settings-row">
          <span>Who can use this panel</span>
          <select
            .value=${t.access_level}
            @change=${t=>this._update("access_level",t.target.value)}
          >
            <option value="owner_only">Account owner only</option>
            <option value="owner_and_admins">Owner and all administrators</option>
          </select>
        </label>
      </div>

      <div class="card">
        <h3>MFA Non-Compliance Policy</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Home Assistant core has no hook to <em>require</em> a second factor at login —
          this can only ever <span class="tag cosmetic">audit</span> that gap, or take the
          one real action core does expose:
          <span class="tag enforced">enforced</span> deactivating an admin account that
          stays out of compliance past the grace period below. The account owner is never
          evaluated or deactivated by this policy.
        </p>
        <label class="settings-row">
          <span>Policy for admins without MFA enabled</span>
          <select
            .value=${t.mfa_policy}
            @change=${t=>this._update("mfa_policy",t.target.value)}
          >
            <option value="audit_only">Audit only — flag via Repairs, never act</option>
            <option value="auto_deactivate">Deactivate after grace period</option>
          </select>
        </label>
        <label class="settings-row">
          <span>Grace period (days)</span>
          <input
            type="number"
            min="1"
            max="365"
            .value=${String(t.mfa_grace_period_days)}
            ?disabled=${"auto_deactivate"!==t.mfa_policy}
            @change=${t=>this._update("mfa_grace_period_days",Number(t.target.value))}
          />
        </label>
      </div>

      <div class="card">
        <h3>Device Vulnerability Scanning</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          <span class="tag cosmetic">best-effort</span> CVE correlation is a heuristic
          vendor/model match against NVD, not a confirmed exploit — absence of a match is
          not evidence a device is secure.
        </p>
        <label class="settings-row">
          <span>
            Look up device CVEs against NIST's NVD
            <span class="muted" style="display:block;font-size:11.5px;"
              >While on, device manufacturer and model strings are sent to
              NIST's NVD (the U.S. National Vulnerability Database) to find
              candidate CVEs. Turning this off stops that lookup entirely.</span
            >
          </span>
          <input
            type="checkbox"
            .checked=${t.nvd_lookups_enabled}
            @change=${t=>this._update("nvd_lookups_enabled",t.target.checked)}
          />
        </label>
        ${this._renderSecretField("NVD API key (optional — raises the public rate limit)","nvd_api_key",!!t.nvd_api_key_set)}
      </div>

      ${this._renderThresholdsCard(t)}

      <div class="card">
        <h3>Integration Security (Provenance)</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          A <strong>provenance</strong> signal, not a safety verdict — it reflects how much
          is known about where an integration's code comes from, never that the code is safe
          to run. A GitHub token (a fine-grained token with public read access is enough)
          lets the Integration Security tab collect release, signing, maintenance,
          popularity, and archived-status signals for integrations with a known GitHub repo.
        </p>
        ${this._renderSecretField("GitHub API token (optional)","github_token",!!t.github_token_set)}
      </div>

      <div class="card">
        <h3>UniFi Network</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Connects directly to a UniFi console over your LAN with a
          <strong>local API key</strong> (UniFi OS → Settings → Control Plane →
          Integrations) to populate the <strong>Network</strong> tab — status, WAN
          throughput, clients, and network devices. Read-only; nothing is ever changed
          on the controller, and no data leaves your network.
        </p>
        <label class="settings-row">
          <span>Controller host or IP</span>
          <input
            type="text"
            placeholder="e.g. 192.168.1.1"
            .value=${t.unifi_network_host??""}
            @change=${t=>{const e=t.target.value.trim();this._update("unifi_network_host",e||null)}}
          />
        </label>
        ${this._renderSecretField("Local API key","unifi_network_api_key",!!t.unifi_network_api_key_set)}
        <label class="settings-row">
          <span>
            Verify TLS certificate
            <span class="muted" style="display:block;font-size:11.5px;"
              >Off by default — UniFi consoles ship a self-signed certificate.</span
            >
          </span>
          <input
            type="checkbox"
            .checked=${t.unifi_network_verify_ssl}
            @change=${t=>this._update("unifi_network_verify_ssl",t.target.checked)}
          />
        </label>
      </div>

      <div class="card">
        <h3>UniFi Protect</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          A second local API key for a UniFi Protect console, surfaced as a compact
          camera-status card on the Network tab. Same local-only, read-only posture as
          Network above.
        </p>
        <label class="settings-row">
          <span>Protect host or IP</span>
          <input
            type="text"
            placeholder="e.g. 192.168.1.1"
            .value=${t.unifi_protect_host??""}
            @change=${t=>{const e=t.target.value.trim();this._update("unifi_protect_host",e||null)}}
          />
        </label>
        ${this._renderSecretField("Local API key","unifi_protect_api_key",!!t.unifi_protect_api_key_set)}
        <label class="settings-row">
          <span>
            Verify TLS certificate
            <span class="muted" style="display:block;font-size:11.5px;"
              >Off by default — UniFi consoles ship a self-signed certificate.</span
            >
          </span>
          <input
            type="checkbox"
            .checked=${t.unifi_protect_verify_ssl}
            @change=${t=>this._update("unifi_protect_verify_ssl",t.target.checked)}
          />
        </label>
      </div>

      <div class="card">
        <h3>Pi-hole</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Connects directly to a Pi-hole v6 instance over your LAN with its
          <strong>app password</strong> (Pi-hole → Settings → API → App password) to
          populate the <strong>Network Security</strong> tab's DNS section — blocking
          status, query totals, and whether the IoT subnet below has its own Pi-hole
          client group. Read-only; nothing is ever toggled or reassigned on Pi-hole.
        </p>
        <label class="settings-row">
          <span>Pi-hole host or IP</span>
          <input
            type="text"
            placeholder="e.g. pi.hole or 192.168.1.5"
            .value=${t.pihole_host??""}
            @change=${t=>{const e=t.target.value.trim();this._update("pihole_host",e||null)}}
          />
        </label>
        ${this._renderSecretField("App password","pihole_api_key",!!t.pihole_api_key_set)}
        <label class="settings-row">
          <span>
            Verify TLS certificate
            <span class="muted" style="display:block;font-size:11.5px;"
              >Off by default — most home Pi-hole instances are plain HTTP on the LAN.</span
            >
          </span>
          <input
            type="checkbox"
            .checked=${t.pihole_verify_ssl}
            @change=${t=>this._update("pihole_verify_ssl",t.target.checked)}
          />
        </label>
        <label class="settings-row">
          <span>
            IoT network CIDR
            <span class="muted" style="display:block;font-size:11.5px;"
              >The subnet whose DNS your UniFi gateway forwards to Pi-hole, e.g.
              192.168.50.0/24. Used only to check whether it has a dedicated Pi-hole
              client group — never to configure DNS itself.</span
            >
          </span>
          <input
            type="text"
            placeholder="e.g. 192.168.50.0/24"
            .value=${t.pihole_iot_cidr??""}
            @change=${t=>{const e=t.target.value.trim();this._update("pihole_iot_cidr",e||null)}}
          />
        </label>
      </div>

      <div class="card">
        <h3>Integration Security Scanner</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Static analysis of every installed integration's source, run on the weekly
          sweep below or on demand from the Scanner tab.
        </p>
        <label class="settings-row">
          <span>Run the weekly scan automatically</span>
          <input
            type="checkbox"
            .checked=${t.scanner_enabled}
            @change=${t=>this._update("scanner_enabled",t.target.checked)}
          />
        </label>
        <label class="settings-row">
          <span>
            Include network-reachability checks
            <span class="muted" style="display:block;font-size:11.5px;"
              >Best-effort connectivity probes against configured device hosts — off by
              default since it makes outbound requests.</span
            >
          </span>
          <input
            type="checkbox"
            .checked=${t.scanner_network_checks_enabled}
            @change=${t=>this._update("scanner_network_checks_enabled",t.target.checked)}
          />
        </label>
      </div>

      <div class="card">
        <h3>Audit Log</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          <span class="tag enforced">enforced</span> Hash-chained JSONL, rotated on
          whichever of these two limits is hit first — see the Audit Log tab's
          <code>Verify chain</code> action.
        </p>
        <label class="settings-row">
          <span>Retention (days)</span>
          <input
            type="number"
            min="7"
            max="3650"
            .value=${String(t.audit_retention_days)}
            @change=${t=>this._update("audit_retention_days",Number(t.target.value))}
          />
        </label>
        <label class="settings-row">
          <span>Maximum size (MB)</span>
          <input
            type="number"
            min="1"
            .value=${String(Math.round(t.audit_max_bytes/Ue))}
            @change=${t=>this._update("audit_max_bytes",Math.round(Number(t.target.value)*Ue))}
          />
        </label>
      </div>

      <div class="card">
        <h3>SIEM / Syslog Export</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Exports finalized hash-chained audit records as RFC 5424 with JSON or
          CEF 0, or as bare canonical JSON for collectors that explicitly require
          it. TCP and TLS retain RFC 6587 octet framing. This stays disabled until
          a destination is configured.
        </p>
        <label class="settings-row">
          <span>
            Payload format
            <span class="muted" style="display:block;font-size:11.5px;"
              >Independent of the UDP, TCP, or TLS transport below.</span
            >
          </span>
          <select
            .value=${t.syslog_format}
            @change=${t=>this._update("syslog_format",t.target.value)}
          >
            <option value="rfc5424_json">RFC 5424 + Raw audit JSON (default)</option>
            <option value="cef">RFC 5424 + CEF 0</option>
            <option value="raw_json">Bare Raw JSON (collector compatibility)</option>
          </select>
        </label>
        ${"raw_json"===t.syslog_format?B`<p class="muted" style="font-size:12px;color:var(--warning-color,#ffa600);">
              Bare Raw JSON has no RFC 5424 envelope. Use it only when the receiver
              explicitly requires JSON-only input; RFC 5424 + JSON remains the
              standards-based default.
            </p>`:""}
        <label class="settings-row">
          <span>Transport</span>
          <select
            .value=${t.syslog_transport}
            @change=${t=>this._update("syslog_transport",t.target.value)}
          >
            <option value="disabled">Disabled</option>
            <option value="udp">UDP (unencrypted fallback)</option>
            <option value="tcp">TCP (unencrypted fallback)</option>
            <option value="tls">TLS over TCP</option>
          </select>
        </label>
        ${"udp"===t.syslog_transport||"tcp"===t.syslog_transport?B`<p class="muted" style="font-size:12px;color:var(--warning-color,#ffa600);">
              UDP/TCP Syslog is unencrypted. Restrict it to a dedicated management
              VLAN or VPN path and migrate to TLS when certificates are assigned.
            </p>`:""}
        <label class="settings-row">
          <span>SIEM host or IP</span>
          <input
            type="text"
            placeholder="e.g. sem.example.lan"
            .value=${t.syslog_host??""}
            @change=${t=>{const e=t.target.value.trim();this._update("syslog_host",e||null)}}
          />
        </label>
        <label class="settings-row">
          <span>Port <span class="muted" style="display:block;font-size:11.5px;">Common: 514 UDP/TCP, 6514 TLS</span></span>
          <input
            type="number"
            min="1"
            max="65535"
            .value=${String(t.syslog_port)}
            @change=${t=>this._update("syslog_port",Number(t.target.value))}
          />
        </label>
        <label class="settings-row">
          <span>Facility</span>
          <select
            .value=${String(t.syslog_facility)}
            @change=${t=>this._update("syslog_facility",Number(t.target.value))}
          >
            ${Array.from({length:8},(t,e)=>B`<option value=${String(16+e)}>local${e}</option>`)}
          </select>
        </label>
        ${"tls"===t.syslog_transport?B`<label class="settings-row">
              <span>
                Verify SIEM TLS certificate
                <span class="muted" style="display:block;font-size:11.5px;"
                  >On by default. Turn off only while the receiver uses a self-signed
                  certificate, then re-enable after certificate assignment.</span
                >
              </span>
              <input
                type="checkbox"
                .checked=${t.syslog_tls_verify}
                @change=${t=>this._update("syslog_tls_verify",t.target.checked)}
              />
            </label>`:""}
        ${t.syslog_status?B`<p class="muted" style="font-size:12px;">
              Status: ${t.syslog_status.last_error?`error — ${t.syslog_status.last_error}`:t.syslog_status.connected?"connected":t.syslog_status.enabled?"waiting for first delivery":"disabled"}.
              Sent ${t.syslog_status.sent}; queued ${t.syslog_status.queued}; dropped
              ${t.syslog_status.dropped}. Format ${t.syslog_status.format}.
            </p>`:""}
      </div>

      <div class="card">
        <h3>Security Integrations Health</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          What shows up in the always-present Dashboard security card. A source stays on
          by default — a device or integration you haven't installed just reports "not
          installed" rather than being hidden, and turning a toggle off here only affects
          this dashboard section, nothing else.
        </p>
        ${Me.map(({domain:e,label:s})=>B`
            <label class="settings-row">
              <span>${s}</span>
              <input
                type="checkbox"
                .checked=${t.security_sources_enabled?.[e]??!0}
                @change=${t=>this._updateSecuritySource(e,t.target.checked)}
              />
            </label>
          `)}
        <h4 style="margin:16px 0 4px;font-size:12px;text-transform:uppercase;letter-spacing:0.03em;color:var(--secondary-text-color);">
          Integrations Loaded
        </h4>
        ${He.map(({domain:t,label:e})=>this._renderIntegrationRow(t,e))}
      </div>

      <div class="card">
        <h3>Host Probe Add-on</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Real socket-level port visibility on the Home Assistant host needs the optional
          <strong>HA SOC Probe</strong> companion add-on — see the Scanner tab's Host
          Probe card for its current status, and the project README for install steps.
          Nothing to configure here; the add-on's own scan interval is set from its own
          add-on Configuration tab.
        </p>
      </div>
    `}};Be.styles=Ft,t([ht({attribute:!1})],Be.prototype,"hass",void 0),t([ut()],Be.prototype,"_settings",void 0),t([ut()],Be.prototype,"_security",void 0),t([ut()],Be.prototype,"_thresholds",void 0),t([ut()],Be.prototype,"_loading",void 0),t([ut()],Be.prototype,"_error",void 0),Be=t([dt("ha-soc-settings-view")],Be);const je=[{id:"dashboard",label:"Dashboard"},{id:"network",label:"Network"},{id:"network_security",label:"Network Security"},{id:"entity_remap",label:"Entity ReMap"},{id:"integration_security",label:"Integration Security"},{id:"users",label:"Users & Access"},{id:"permissions",label:"Permissions"},{id:"audit",label:"Audit Log"},{id:"peripherals",label:"Local Peripherals"},{id:"scanner",label:"Scanner"},{id:"logs",label:"Logs"},{id:"settings",label:"Settings",ownerOnly:!0}];let We=class extends nt{constructor(){super(...arguments),this._tab="dashboard",this._access=null,this._version=null,this._probe=null,this._customizeMode=!1,this._pendingNetworkFilter=null}connectedCallback(){super.connectedCallback(),this._loadAccess(),this._loadFooterInfo()}async _loadAccess(){try{this._access=await Ct(this.hass)}catch{this._access={is_owner:!1,access_level:"owner_only",allowed:!1}}}async _loadFooterInfo(){try{this._version=(await(t=this.hass,gt(t,{type:"ha_soc/version/get"}))).version}catch{this._version=null}var t;try{this._probe=await At(this.hass)}catch{this._probe=null}}_renderFooter(){if(!this._version)return B``;const t=this._probe?.installed&&this._probe.version?` · HA SOC Probe v${this._probe.version}`:"";return B`<div class="footer">HA SOC v${this._version}${t}</div>`}render(){if(null===this._access)return B`<div class="header">🛡️ HA SOC</div>`;if(!this._access.allowed)return B`
        <div class="denied">
          <div class="icon">🛡️🚫</div>
          <h2>Access restricted</h2>
          <p>
            HA SOC is currently set to <strong>account owner only</strong>. Your account
            is an administrator, but not the account owner, so this panel and its data
            aren't reachable from here.
          </p>
          <p>
            The owner can open this up to every administrator from
            <strong>Settings → Devices &amp; Services → HA SOC → Configure</strong>, or
            from this panel's own Settings tab once they've signed in.
          </p>
        </div>
        ${this._renderFooter()}
      `;const t=je.find(t=>t.id===this._tab)?.label??"Dashboard";return B`
      <div class="header">
        <div class="brand">
          <span class="brand-mark">SOC</span>
          <span>
            <span class="brand-title">HA SOC</span>
            <span class="brand-context">${t}</span>
          </span>
        </div>
        ${"settings"===this._tab?B``:B`
              <button
                type="button"
                class="customize-btn ${this._customizeMode?"active":""}"
                @click=${()=>this._customizeMode=!this._customizeMode}
              >
                ${this._customizeMode?"Done":"Customize"}
              </button>
            `}
      </div>
      <div class="tabs">
        ${je.map(t=>!!t.ownerOnly&&!this._access?.is_owner?B`
              <button type="button" class="tab disabled" title="Only available to the account owner" disabled>
                ${t.label}<span class="lock">🔒</span>
              </button>
            `:B`
            <button
              type="button"
              class="tab ${this._tab===t.id?"active":""}"
              aria-pressed=${this._tab===t.id?"true":"false"}
              @click=${()=>this._selectTab(t.id)}
            >
              ${t.label}
            </button>
          `)}
      </div>
      <div @ha-soc-navigate=${this._onNavigate}>${this._renderTab()}</div>
      ${this._renderFooter()}
    `}_selectTab(t){this._tab=t,this._customizeMode=!1}_onNavigate(t){this._tab=t.detail.tab,this._customizeMode=!1,t.detail.clientFilter&&(this._pendingNetworkFilter=t.detail.clientFilter)}_renderTab(){const t=this._customizeMode;switch(this._tab){case"users":return B`<ha-soc-users-view .hass=${this.hass} .customizeMode=${t}></ha-soc-users-view>`;case"audit":return B`<ha-soc-audit-view .hass=${this.hass} .customizeMode=${t}></ha-soc-audit-view>`;case"permissions":return B`<ha-soc-permissions-view .hass=${this.hass} .customizeMode=${t}></ha-soc-permissions-view>`;case"scanner":return B`<ha-soc-scanner-view .hass=${this.hass} .customizeMode=${t}></ha-soc-scanner-view>`;case"logs":return B`<ha-soc-logs-view .hass=${this.hass} .customizeMode=${t}></ha-soc-logs-view>`;case"peripherals":return B`<ha-soc-peripherals-view .hass=${this.hass} .customizeMode=${t}></ha-soc-peripherals-view>`;case"network":return B`<ha-soc-network-view
          .hass=${this.hass}
          .customizeMode=${t}
          .initialClientFilter=${this._pendingNetworkFilter}
          @client-filter-consumed=${()=>this._pendingNetworkFilter=null}
        ></ha-soc-network-view>`;case"network_security":return B`<ha-soc-network-security-view
          .hass=${this.hass}
          .customizeMode=${t}
        ></ha-soc-network-security-view>`;case"entity_remap":return B`<ha-soc-entity-remap-view .hass=${this.hass} .customizeMode=${t}></ha-soc-entity-remap-view>`;case"integration_security":return B`<ha-soc-integration-security-view
          .hass=${this.hass}
          .customizeMode=${t}
        ></ha-soc-integration-security-view>`;case"settings":return this._access?.is_owner?B`<ha-soc-settings-view .hass=${this.hass}></ha-soc-settings-view>`:B`<div class="denied"><div class="icon">🔒</div><h2>Owner only</h2>
            <p>The Settings tab is available to the account owner only.</p></div>`;default:return B`<ha-soc-dashboard-view .hass=${this.hass} .customizeMode=${t}></ha-soc-dashboard-view>`}}};We.styles=o`
    :host {
      display: block;
      background: var(--primary-background-color);
      min-height: 100vh;
    }
    .tabs {
      display: flex;
      gap: 6px;
      border-top: 1px solid var(--divider-color);
      border-bottom: 1px solid var(--divider-color);
      padding: 9px max(16px, calc((100% - 1400px) / 2));
      background: var(--card-background-color, #fff);
      overflow-x: auto;
      position: sticky;
      top: 0;
      z-index: 5;
      scrollbar-width: thin;
    }
    .tab {
      appearance: none;
      font: inherit;
      background: transparent;
      border: 1px solid transparent;
      border-radius: 9px;
      padding: 8px 11px;
      cursor: pointer;
      font-size: 13px;
      font-weight: 550;
      color: var(--secondary-text-color);
      white-space: nowrap;
    }
    .tab:hover,
    .tab:focus-visible {
      color: var(--primary-text-color);
      background: rgba(var(--rgb-primary-text-color, 0, 0, 0), 0.045);
      outline: none;
    }
    .tab.active {
      color: var(--primary-color);
      border-color: rgba(var(--rgb-primary-color, 3, 155, 229), 0.24);
      background: rgba(var(--rgb-primary-color, 3, 155, 229), 0.1);
    }
    .tab.disabled {
      color: var(--disabled-text-color, #b0b0b0);
      cursor: not-allowed;
    }
    .tab.disabled .lock {
      font-size: 11px;
      margin-left: 4px;
      opacity: 0.8;
    }
    .header {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 17px max(16px, calc((100% - 1400px) / 2)) 14px;
      color: var(--primary-text-color);
      background: var(--card-background-color, #fff);
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 10px;
      flex: 1;
    }
    .brand-mark {
      width: 34px;
      height: 34px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      border-radius: 10px;
      background: var(--primary-color);
      color: #fff;
      font-size: 12px;
      font-weight: 750;
      letter-spacing: 0.04em;
    }
    .brand-title {
      display: block;
      font-size: 18px;
      font-weight: 680;
      line-height: 1.15;
    }
    .brand-context {
      display: block;
      margin-top: 2px;
      color: var(--secondary-text-color);
      font-size: 11.5px;
    }
    .customize-btn {
      font-size: 13px;
      font-weight: 500;
      padding: 7px 14px;
      border-radius: 100px;
      border: 1px solid var(--divider-color);
      background: var(--card-background-color, #fff);
      color: var(--primary-text-color);
      cursor: pointer;
    }
    .customize-btn.active {
      background: var(--primary-color);
      border-color: var(--primary-color);
      color: #fff;
    }
    .denied {
      max-width: 480px;
      margin: 15vh auto 0;
      padding: 32px;
      text-align: center;
      color: var(--primary-text-color);
    }
    .denied .icon {
      font-size: 40px;
    }
    .denied h2 {
      margin: 12px 0 4px;
      font-size: 18px;
    }
    .denied p {
      color: var(--secondary-text-color);
      font-size: 13.5px;
      line-height: 1.5;
    }
    .footer {
      padding: 10px 16px 14px;
      font-size: 11px;
      color: var(--secondary-text-color);
      text-align: center;
    }
    @media (max-width: 600px) {
      .header {
        padding-top: 12px;
      }
      .brand-context {
        display: none;
      }
      .customize-btn {
        padding: 7px 10px;
      }
    }
  `,t([ht({attribute:!1})],We.prototype,"hass",void 0),t([ht({attribute:!1})],We.prototype,"narrow",void 0),t([ht({attribute:!1})],We.prototype,"panel",void 0),t([ut()],We.prototype,"_tab",void 0),t([ut()],We.prototype,"_access",void 0),t([ut()],We.prototype,"_version",void 0),t([ut()],We.prototype,"_probe",void 0),t([ut()],We.prototype,"_customizeMode",void 0),t([ut()],We.prototype,"_pendingNetworkFilter",void 0),We=t([dt("ha-soc-panel")],We);export{We as HaSocPanel};
