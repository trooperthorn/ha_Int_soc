function t(t,e,s,i){var a,n=arguments.length,o=n<3?e:null===i?i=Object.getOwnPropertyDescriptor(e,s):i;if("object"==typeof Reflect&&"function"==typeof Reflect.decorate)o=Reflect.decorate(t,e,s,i);else for(var r=t.length-1;r>=0;r--)(a=t[r])&&(o=(n<3?a(o):n>3?a(e,s,o):a(e,s))||o);return n>3&&o&&Object.defineProperty(e,s,o),o}"function"==typeof SuppressedError&&SuppressedError;
/**
 * @license
 * Copyright 2019 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const e=globalThis,s=e.ShadowRoot&&(void 0===e.ShadyCSS||e.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,i=Symbol(),a=new WeakMap;let n=class{constructor(t,e,s){if(this._$cssResult$=!0,s!==i)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=t,this.t=e}get styleSheet(){let t=this.o;const e=this.t;if(s&&void 0===t){const s=void 0!==e&&1===e.length;s&&(t=a.get(e)),void 0===t&&((this.o=t=new CSSStyleSheet).replaceSync(this.cssText),s&&a.set(e,t))}return t}toString(){return this.cssText}};const o=(t,...e)=>{const s=1===t.length?t[0]:e.reduce((e,s,i)=>e+(t=>{if(!0===t._$cssResult$)return t.cssText;if("number"==typeof t)return t;throw Error("Value passed to 'css' function must be a 'css' function result: "+t+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(s)+t[i+1],t[0]);return new n(s,t,i)},r=s?t=>t:t=>t instanceof CSSStyleSheet?(t=>{let e="";for(const s of t.cssRules)e+=s.cssText;return(t=>new n("string"==typeof t?t:t+"",void 0,i))(e)})(t):t,{is:l,defineProperty:d,getOwnPropertyDescriptor:c,getOwnPropertyNames:h,getOwnPropertySymbols:p,getPrototypeOf:u}=Object,v=globalThis,g=v.trustedTypes,_=g?g.emptyScript:"",y=v.reactiveElementPolyfillSupport,m=(t,e)=>t,b={toAttribute(t,e){switch(e){case Boolean:t=t?_:null;break;case Object:case Array:t=null==t?t:JSON.stringify(t)}return t},fromAttribute(t,e){let s=t;switch(e){case Boolean:s=null!==t;break;case Number:s=null===t?null:Number(t);break;case Object:case Array:try{s=JSON.parse(t)}catch(t){s=null}}return s}},f=(t,e)=>!l(t,e),$={attribute:!0,type:String,converter:b,reflect:!1,useDefault:!1,hasChanged:f};
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */Symbol.metadata??=Symbol("metadata"),v.litPropertyMetadata??=new WeakMap;let w=class extends HTMLElement{static addInitializer(t){this._$Ei(),(this.l??=[]).push(t)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(t,e=$){if(e.state&&(e.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(t)&&((e=Object.create(e)).wrapped=!0),this.elementProperties.set(t,e),!e.noAccessor){const s=Symbol(),i=this.getPropertyDescriptor(t,s,e);void 0!==i&&d(this.prototype,t,i)}}static getPropertyDescriptor(t,e,s){const{get:i,set:a}=c(this.prototype,t)??{get(){return this[e]},set(t){this[e]=t}};return{get:i,set(e){const n=i?.call(this);a?.call(this,e),this.requestUpdate(t,n,s)},configurable:!0,enumerable:!0}}static getPropertyOptions(t){return this.elementProperties.get(t)??$}static _$Ei(){if(this.hasOwnProperty(m("elementProperties")))return;const t=u(this);t.finalize(),void 0!==t.l&&(this.l=[...t.l]),this.elementProperties=new Map(t.elementProperties)}static finalize(){if(this.hasOwnProperty(m("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(m("properties"))){const t=this.properties,e=[...h(t),...p(t)];for(const s of e)this.createProperty(s,t[s])}const t=this[Symbol.metadata];if(null!==t){const e=litPropertyMetadata.get(t);if(void 0!==e)for(const[t,s]of e)this.elementProperties.set(t,s)}this._$Eh=new Map;for(const[t,e]of this.elementProperties){const s=this._$Eu(t,e);void 0!==s&&this._$Eh.set(s,t)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(t){const e=[];if(Array.isArray(t)){const s=new Set(t.flat(1/0).reverse());for(const t of s)e.unshift(r(t))}else void 0!==t&&e.push(r(t));return e}static _$Eu(t,e){const s=e.attribute;return!1===s?void 0:"string"==typeof s?s:"string"==typeof t?t.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(t=>this.enableUpdating=t),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(t=>t(this))}addController(t){(this._$EO??=new Set).add(t),void 0!==this.renderRoot&&this.isConnected&&t.hostConnected?.()}removeController(t){this._$EO?.delete(t)}_$E_(){const t=new Map,e=this.constructor.elementProperties;for(const s of e.keys())this.hasOwnProperty(s)&&(t.set(s,this[s]),delete this[s]);t.size>0&&(this._$Ep=t)}createRenderRoot(){const t=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return((t,i)=>{if(s)t.adoptedStyleSheets=i.map(t=>t instanceof CSSStyleSheet?t:t.styleSheet);else for(const s of i){const i=document.createElement("style"),a=e.litNonce;void 0!==a&&i.setAttribute("nonce",a),i.textContent=s.cssText,t.appendChild(i)}})(t,this.constructor.elementStyles),t}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(t=>t.hostConnected?.())}enableUpdating(t){}disconnectedCallback(){this._$EO?.forEach(t=>t.hostDisconnected?.())}attributeChangedCallback(t,e,s){this._$AK(t,s)}_$ET(t,e){const s=this.constructor.elementProperties.get(t),i=this.constructor._$Eu(t,s);if(void 0!==i&&!0===s.reflect){const a=(void 0!==s.converter?.toAttribute?s.converter:b).toAttribute(e,s.type);this._$Em=t,null==a?this.removeAttribute(i):this.setAttribute(i,a),this._$Em=null}}_$AK(t,e){const s=this.constructor,i=s._$Eh.get(t);if(void 0!==i&&this._$Em!==i){const t=s.getPropertyOptions(i),a="function"==typeof t.converter?{fromAttribute:t.converter}:void 0!==t.converter?.fromAttribute?t.converter:b;this._$Em=i;const n=a.fromAttribute(e,t.type);this[i]=n??this._$Ej?.get(i)??n,this._$Em=null}}requestUpdate(t,e,s,i=!1,a){if(void 0!==t){const n=this.constructor;if(!1===i&&(a=this[t]),s??=n.getPropertyOptions(t),!((s.hasChanged??f)(a,e)||s.useDefault&&s.reflect&&a===this._$Ej?.get(t)&&!this.hasAttribute(n._$Eu(t,s))))return;this.C(t,e,s)}!1===this.isUpdatePending&&(this._$ES=this._$EP())}C(t,e,{useDefault:s,reflect:i,wrapped:a},n){s&&!(this._$Ej??=new Map).has(t)&&(this._$Ej.set(t,n??e??this[t]),!0!==a||void 0!==n)||(this._$AL.has(t)||(this.hasUpdated||s||(e=void 0),this._$AL.set(t,e)),!0===i&&this._$Em!==t&&(this._$Eq??=new Set).add(t))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(t){Promise.reject(t)}const t=this.scheduleUpdate();return null!=t&&await t,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(const[t,e]of this._$Ep)this[t]=e;this._$Ep=void 0}const t=this.constructor.elementProperties;if(t.size>0)for(const[e,s]of t){const{wrapped:t}=s,i=this[e];!0!==t||this._$AL.has(e)||void 0===i||this.C(e,void 0,s,i)}}let t=!1;const e=this._$AL;try{t=this.shouldUpdate(e),t?(this.willUpdate(e),this._$EO?.forEach(t=>t.hostUpdate?.()),this.update(e)):this._$EM()}catch(e){throw t=!1,this._$EM(),e}t&&this._$AE(e)}willUpdate(t){}_$AE(t){this._$EO?.forEach(t=>t.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(t)),this.updated(t)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(t){return!0}update(t){this._$Eq&&=this._$Eq.forEach(t=>this._$ET(t,this[t])),this._$EM()}updated(t){}firstUpdated(t){}};w.elementStyles=[],w.shadowRootOptions={mode:"open"},w[m("elementProperties")]=new Map,w[m("finalized")]=new Map,y?.({ReactiveElement:w}),(v.reactiveElementVersions??=[]).push("2.1.2");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const x=globalThis,k=t=>t,S=x.trustedTypes,A=S?S.createPolicy("lit-html",{createHTML:t=>t}):void 0,C="$lit$",P=`lit$${Math.random().toFixed(9).slice(2)}$`,F="?"+P,E=`<${F}>`,z=document,I=()=>z.createComment(""),R=t=>null===t||"object"!=typeof t&&"function"!=typeof t,L=Array.isArray,U="[ \t\n\f\r]",N=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,D=/-->/g,H=/>/g,O=RegExp(`>|${U}(?:([^\\s"'>=/]+)(${U}*=${U}*(?:[^ \t\n\f\r"'\`<>=]|("|')|))|$)`,"g"),T=/'/g,M=/"/g,V=/^(?:script|style|textarea|title)$/i,B=(t=>(e,...s)=>({_$litType$:t,strings:e,values:s}))(1),j=Symbol.for("lit-noChange"),W=Symbol.for("lit-nothing"),q=new WeakMap,G=z.createTreeWalker(z,129);function K(t,e){if(!L(t)||!t.hasOwnProperty("raw"))throw Error("invalid template strings array");return void 0!==A?A.createHTML(e):e}const Y=(t,e)=>{const s=t.length-1,i=[];let a,n=2===e?"<svg>":3===e?"<math>":"",o=N;for(let e=0;e<s;e++){const s=t[e];let r,l,d=-1,c=0;for(;c<s.length&&(o.lastIndex=c,l=o.exec(s),null!==l);)c=o.lastIndex,o===N?"!--"===l[1]?o=D:void 0!==l[1]?o=H:void 0!==l[2]?(V.test(l[2])&&(a=RegExp("</"+l[2],"g")),o=O):void 0!==l[3]&&(o=O):o===O?">"===l[0]?(o=a??N,d=-1):void 0===l[1]?d=-2:(d=o.lastIndex-l[2].length,r=l[1],o=void 0===l[3]?O:'"'===l[3]?M:T):o===M||o===T?o=O:o===D||o===H?o=N:(o=O,a=void 0);const h=o===O&&t[e+1].startsWith("/>")?" ":"";n+=o===N?s+E:d>=0?(i.push(r),s.slice(0,d)+C+s.slice(d)+P+h):s+P+(-2===d?e:h)}return[K(t,n+(t[s]||"<?>")+(2===e?"</svg>":3===e?"</math>":"")),i]};class Z{constructor({strings:t,_$litType$:e},s){let i;this.parts=[];let a=0,n=0;const o=t.length-1,r=this.parts,[l,d]=Y(t,e);if(this.el=Z.createElement(l,s),G.currentNode=this.el.content,2===e||3===e){const t=this.el.content.firstChild;t.replaceWith(...t.childNodes)}for(;null!==(i=G.nextNode())&&r.length<o;){if(1===i.nodeType){if(i.hasAttributes())for(const t of i.getAttributeNames())if(t.endsWith(C)){const e=d[n++],s=i.getAttribute(t).split(P),o=/([.?@])?(.*)/.exec(e);r.push({type:1,index:a,name:o[2],strings:s,ctor:"."===o[1]?et:"?"===o[1]?st:"@"===o[1]?it:tt}),i.removeAttribute(t)}else t.startsWith(P)&&(r.push({type:6,index:a}),i.removeAttribute(t));if(V.test(i.tagName)){const t=i.textContent.split(P),e=t.length-1;if(e>0){i.textContent=S?S.emptyScript:"";for(let s=0;s<e;s++)i.append(t[s],I()),G.nextNode(),r.push({type:2,index:++a});i.append(t[e],I())}}}else if(8===i.nodeType)if(i.data===F)r.push({type:2,index:a});else{let t=-1;for(;-1!==(t=i.data.indexOf(P,t+1));)r.push({type:7,index:a}),t+=P.length-1}a++}}static createElement(t,e){const s=z.createElement("template");return s.innerHTML=t,s}}function J(t,e,s=t,i){if(e===j)return e;let a=void 0!==i?s._$Co?.[i]:s._$Cl;const n=R(e)?void 0:e._$litDirective$;return a?.constructor!==n&&(a?._$AO?.(!1),void 0===n?a=void 0:(a=new n(t),a._$AT(t,s,i)),void 0!==i?(s._$Co??=[])[i]=a:s._$Cl=a),void 0!==a&&(e=J(t,a._$AS(t,e.values),a,i)),e}class Q{constructor(t,e){this._$AV=[],this._$AN=void 0,this._$AD=t,this._$AM=e}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(t){const{el:{content:e},parts:s}=this._$AD,i=(t?.creationScope??z).importNode(e,!0);G.currentNode=i;let a=G.nextNode(),n=0,o=0,r=s[0];for(;void 0!==r;){if(n===r.index){let e;2===r.type?e=new X(a,a.nextSibling,this,t):1===r.type?e=new r.ctor(a,r.name,r.strings,this,t):6===r.type&&(e=new at(a,this,t)),this._$AV.push(e),r=s[++o]}n!==r?.index&&(a=G.nextNode(),n++)}return G.currentNode=z,i}p(t){let e=0;for(const s of this._$AV)void 0!==s&&(void 0!==s.strings?(s._$AI(t,s,e),e+=s.strings.length-2):s._$AI(t[e])),e++}}class X{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(t,e,s,i){this.type=2,this._$AH=W,this._$AN=void 0,this._$AA=t,this._$AB=e,this._$AM=s,this.options=i,this._$Cv=i?.isConnected??!0}get parentNode(){let t=this._$AA.parentNode;const e=this._$AM;return void 0!==e&&11===t?.nodeType&&(t=e.parentNode),t}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(t,e=this){t=J(this,t,e),R(t)?t===W||null==t||""===t?(this._$AH!==W&&this._$AR(),this._$AH=W):t!==this._$AH&&t!==j&&this._(t):void 0!==t._$litType$?this.$(t):void 0!==t.nodeType?this.T(t):(t=>L(t)||"function"==typeof t?.[Symbol.iterator])(t)?this.k(t):this._(t)}O(t){return this._$AA.parentNode.insertBefore(t,this._$AB)}T(t){this._$AH!==t&&(this._$AR(),this._$AH=this.O(t))}_(t){this._$AH!==W&&R(this._$AH)?this._$AA.nextSibling.data=t:this.T(z.createTextNode(t)),this._$AH=t}$(t){const{values:e,_$litType$:s}=t,i="number"==typeof s?this._$AC(t):(void 0===s.el&&(s.el=Z.createElement(K(s.h,s.h[0]),this.options)),s);if(this._$AH?._$AD===i)this._$AH.p(e);else{const t=new Q(i,this),s=t.u(this.options);t.p(e),this.T(s),this._$AH=t}}_$AC(t){let e=q.get(t.strings);return void 0===e&&q.set(t.strings,e=new Z(t)),e}k(t){L(this._$AH)||(this._$AH=[],this._$AR());const e=this._$AH;let s,i=0;for(const a of t)i===e.length?e.push(s=new X(this.O(I()),this.O(I()),this,this.options)):s=e[i],s._$AI(a),i++;i<e.length&&(this._$AR(s&&s._$AB.nextSibling,i),e.length=i)}_$AR(t=this._$AA.nextSibling,e){for(this._$AP?.(!1,!0,e);t!==this._$AB;){const e=k(t).nextSibling;k(t).remove(),t=e}}setConnected(t){void 0===this._$AM&&(this._$Cv=t,this._$AP?.(t))}}class tt{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(t,e,s,i,a){this.type=1,this._$AH=W,this._$AN=void 0,this.element=t,this.name=e,this._$AM=i,this.options=a,s.length>2||""!==s[0]||""!==s[1]?(this._$AH=Array(s.length-1).fill(new String),this.strings=s):this._$AH=W}_$AI(t,e=this,s,i){const a=this.strings;let n=!1;if(void 0===a)t=J(this,t,e,0),n=!R(t)||t!==this._$AH&&t!==j,n&&(this._$AH=t);else{const i=t;let o,r;for(t=a[0],o=0;o<a.length-1;o++)r=J(this,i[s+o],e,o),r===j&&(r=this._$AH[o]),n||=!R(r)||r!==this._$AH[o],r===W?t=W:t!==W&&(t+=(r??"")+a[o+1]),this._$AH[o]=r}n&&!i&&this.j(t)}j(t){t===W?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,t??"")}}class et extends tt{constructor(){super(...arguments),this.type=3}j(t){this.element[this.name]=t===W?void 0:t}}class st extends tt{constructor(){super(...arguments),this.type=4}j(t){this.element.toggleAttribute(this.name,!!t&&t!==W)}}class it extends tt{constructor(t,e,s,i,a){super(t,e,s,i,a),this.type=5}_$AI(t,e=this){if((t=J(this,t,e,0)??W)===j)return;const s=this._$AH,i=t===W&&s!==W||t.capture!==s.capture||t.once!==s.once||t.passive!==s.passive,a=t!==W&&(s===W||i);i&&this.element.removeEventListener(this.name,this,s),a&&this.element.addEventListener(this.name,this,t),this._$AH=t}handleEvent(t){"function"==typeof this._$AH?this._$AH.call(this.options?.host??this.element,t):this._$AH.handleEvent(t)}}class at{constructor(t,e,s){this.element=t,this.type=6,this._$AN=void 0,this._$AM=e,this.options=s}get _$AU(){return this._$AM._$AU}_$AI(t){J(this,t)}}const nt=x.litHtmlPolyfillSupport;nt?.(Z,X),(x.litHtmlVersions??=[]).push("3.3.3");const ot=globalThis;
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */class rt extends w{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){const t=super.createRenderRoot();return this.renderOptions.renderBefore??=t.firstChild,t}update(t){const e=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(t),this._$Do=((t,e,s)=>{const i=s?.renderBefore??e;let a=i._$litPart$;if(void 0===a){const t=s?.renderBefore??null;i._$litPart$=a=new X(e.insertBefore(I(),t),t,void 0,s??{})}return a._$AI(t),a})(e,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return j}}rt._$litElement$=!0,rt.finalized=!0,ot.litElementHydrateSupport?.({LitElement:rt});const lt=ot.litElementPolyfillSupport;lt?.({LitElement:rt}),(ot.litElementVersions??=[]).push("4.2.2");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const dt=t=>(e,s)=>{void 0!==s?s.addInitializer(()=>{customElements.define(t,e)}):customElements.define(t,e)},ct={attribute:!0,type:String,converter:b,reflect:!1,hasChanged:f},ht=(t=ct,e,s)=>{const{kind:i,metadata:a}=s;let n=globalThis.litPropertyMetadata.get(a);if(void 0===n&&globalThis.litPropertyMetadata.set(a,n=new Map),"setter"===i&&((t=Object.create(t)).wrapped=!0),n.set(s.name,t),"accessor"===i){const{name:i}=s;return{set(s){const a=e.get.call(this);e.set.call(this,s),this.requestUpdate(i,a,t,!0,s)},init(e){return void 0!==e&&this.C(i,void 0,t,e),e}}}if("setter"===i){const{name:i}=s;return function(s){const a=this[i];e.call(this,s),this.requestUpdate(i,a,t,!0,s)}}throw Error("Unsupported decorator location: "+i)};
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */function pt(t){return(e,s)=>"object"==typeof s?ht(t,e,s):((t,e,s)=>{const i=e.hasOwnProperty(s);return e.constructor.createProperty(s,t),i?Object.getOwnPropertyDescriptor(e,s):void 0})(t,e,s)}
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */function ut(t){return pt({...t,state:!0,attribute:!1})}const vt=(t,e)=>t.callWS(e),gt=t=>vt(t,{type:"ha_soc/users/list"}).then(t=>t.users),_t=t=>vt(t,{type:"ha_soc/risk/list"}).then(t=>t.risk),yt=(t,e)=>vt(t,{type:"ha_soc/detections/list",status:e}).then(t=>t.detections),mt=(t,e,s)=>vt(t,{type:"ha_soc/detections/set_status",detection_id:e,status:s}),bt=t=>vt(t,{type:"ha_soc/vulns/list"}).then(t=>t.findings),ft=t=>vt(t,{type:"ha_soc/logs/fault"}),$t=t=>vt(t,{type:"ha_soc/health/list"}),wt=t=>vt(t,{type:"ha_soc/dashboard/devices"}),xt=t=>vt(t,{type:"ha_soc/dashboard/integrations"}),kt=t=>vt(t,{type:"ha_soc/probe/status"}),St=t=>vt(t,{type:"ha_soc/firewall/status"}),At=t=>vt(t,{type:"ha_soc/peripherals/list"}),Ct=t=>vt(t,{type:"ha_soc/entity_remap/broken_references"}).then(t=>t.broken),Pt=t=>vt(t,{type:"ha_soc/security_health/list"}),Ft=o`
  :host {
    display: block;
    padding: 16px;
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
    box-shadow: var(--ha-card-box-shadow, 0 1px 2px rgba(0, 0, 0, 0.08));
    padding: 16px;
    margin-bottom: 16px;
  }
  .card h3 {
    margin: 0 0 12px;
    font-size: 15px;
    font-weight: 600;
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
`;let Et=class extends rt{constructor(){super(...arguments),this._users=[],this._risk={},this._loading=!0,this._busyUserId=null}connectedCallback(){super.connectedCallback(),this._load()}async _load(){this._loading=!0;try{const[t,e]=await Promise.all([gt(this.hass),_t(this.hass)]);this._users=t,this._risk=e}finally{this._loading=!1}}_fmtDate(t){if(!t)return"never";return new Date(t).toLocaleString()}async _onDeactivate(t){if(confirm("Deactivate this user? All their sessions will be revoked.")){this._busyUserId=t;try{await((t,e)=>vt(t,{type:"ha_soc/users/deactivate",user_id:e}))(this.hass,t),await this._load()}finally{this._busyUserId=null}}}async _onRevokeAll(t){if(confirm("Revoke every interactive session for this user? Long-lived tokens are kept.")){this._busyUserId=t;try{await((t,e)=>vt(t,{type:"ha_soc/users/revoke_all_sessions",user_id:e}))(this.hass,t),await this._load()}finally{this._busyUserId=null}}}async _onResetPassword(t){const e=prompt("New password for this user (owner-only action):");if(e){this._busyUserId=t;try{const s=await((t,e,s)=>vt(t,{type:"ha_soc/users/set_password",user_id:e,password:s}))(this.hass,t,e);s&&!1===s.ok&&alert("Could not set password — only the account owner can reset another user's password.")}finally{this._busyUserId=null}}}render(){return this._loading?B`<div class="empty">Loading users…</div>`:this._users.length?B`
      <div class="card">
        <h3>Users &amp; Access</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Last login is derived from refresh-token activity — a background token
          refresh looks the same as a fresh interactive login. MFA status is read
          directly from the auth store but cannot be enforced by Home Assistant.
        </p>
        <table>
          <thead>
            <tr>
              <th>User</th>
              <th>Role</th>
              <th>MFA</th>
              <th>Risk</th>
              <th>Last login</th>
              <th>Tokens</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            ${this._users.map(t=>{const e=this._risk[t.id];return B`
                <tr class=${t.is_active?"":"row-disabled"}>
                  <td>
                    <div>${t.name??t.id}</div>
                    ${t.is_owner?B`<span class="tag enforced">owner</span>`:W}
                    ${t.is_active?W:B`<span class="tag cosmetic">deactivated</span>`}
                  </td>
                  <td>${t.is_admin?"Admin":"User"}${t.local_only?" · local only":""}</td>
                  <td>
                    ${t.mfa_enabled?B`<span class="pill good"><span class="dot"></span>enabled</span>`:B`<span class="pill high"><span class="dot"></span>none</span>`}
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
                        @click=${()=>this._onResetPassword(t.id)}
                      >
                        Reset password
                      </button>
                      <button
                        class="ha-btn"
                        ?disabled=${this._busyUserId===t.id}
                        @click=${()=>this._onRevokeAll(t.id)}
                      >
                        Revoke sessions
                      </button>
                      <button
                        class="ha-btn danger"
                        ?disabled=${this._busyUserId===t.id||t.is_owner}
                        @click=${()=>this._onDeactivate(t.id)}
                      >
                        Deactivate
                      </button>
                    </div>
                  </td>
                </tr>
              `})}
          </tbody>
        </table>
      </div>
    `:B`<div class="empty">No users found.</div>`}};Et.styles=Ft,t([pt({attribute:!1})],Et.prototype,"hass",void 0),t([ut()],Et.prototype,"_users",void 0),t([ut()],Et.prototype,"_risk",void 0),t([ut()],Et.prototype,"_loading",void 0),t([ut()],Et.prototype,"_busyUserId",void 0),Et=t([dt("ha-soc-users-view")],Et);const zt=["","service_call","login_ok","login_fail","token_created","user_added","user_updated","user_removed","lovelace_change","entity_registry_change"];let It=class extends rt{constructor(){super(...arguments),this._events=[],this._users=[],this._loading=!0,this._category="",this._userId="",this._verifyResult=null}connectedCallback(){super.connectedCallback(),this._loadUsers(),this._load()}async _loadUsers(){this._users=await gt(this.hass)}async _load(){this._loading=!0;try{this._events=await((t,e={})=>vt(t,{type:"ha_soc/audit/query",...e}).then(t=>t.events))(this.hass,{category:this._category||void 0,user_id:this._userId||void 0,limit:200})}finally{this._loading=!1}}_nameFor(t){return t?this._users.find(e=>e.id===t)?.name??t:"—"}async _onVerify(){var t;this._verifyResult=await(t=this.hass,vt(t,{type:"ha_soc/audit/verify_chain"}))}_onCategoryChange(t){this._category=t.target.value,this._load()}_onUserChange(t){this._userId=t.target.value,this._load()}render(){return B`
      <div class="card">
        <h3>Audit Log</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Every user-attributed service call, user/dashboard change, and
          best-effort login signal. Failed logins carry only a source IP — Home
          Assistant never logs the attempted username on a failed login.
        </p>
        <div class="toolbar">
          <select @change=${this._onCategoryChange}>
            ${zt.map(t=>B`<option value=${t} ?selected=${t===this._category}>${t||"All categories"}</option>`)}
          </select>
          <select @change=${this._onUserChange}>
            <option value="" ?selected=${""===this._userId}>All users</option>
            ${this._users.map(t=>B`<option value=${t.id} ?selected=${t.id===this._userId}>${t.name??t.id}</option>`)}
          </select>
          <span class="spacer"></span>
          <button class="ha-btn" @click=${this._onVerify}>Verify chain integrity</button>
          <button class="ha-btn" @click=${this._load}>Refresh</button>
        </div>
        ${this._verifyResult?B`<p class="${this._verifyResult.ok?"muted":""}" style="font-size:12.5px;">
              ${this._verifyResult.ok?`Chain intact — ${this._verifyResult.records_checked} records checked.`:"Chain broken — see logs for the first mismatched record."}
            </p>`:null}
        ${this._loading?B`<div class="empty">Loading…</div>`:this._events.length?B`
              <table>
                <thead>
                  <tr>
                    <th>Time</th>
                    <th>Category</th>
                    <th>User</th>
                    <th>Action</th>
                    <th>Source</th>
                  </tr>
                </thead>
                <tbody>
                  ${this._events.map(t=>B`
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
    `}};It.styles=Ft,t([pt({attribute:!1})],It.prototype,"hass",void 0),t([ut()],It.prototype,"_events",void 0),t([ut()],It.prototype,"_users",void 0),t([ut()],It.prototype,"_loading",void 0),t([ut()],It.prototype,"_category",void 0),t([ut()],It.prototype,"_userId",void 0),t([ut()],It.prototype,"_verifyResult",void 0),It=t([dt("ha-soc-audit-view")],It);let Rt=class extends rt{constructor(){super(...arguments),this._users=[],this._dashboards=[],this._selected=void 0,this._views=[],this._loading=!0,this._drift=[],this._viewsError=null}connectedCallback(){super.connectedCallback(),this._load()}async _load(){this._loading=!0;try{const[e,s]=await Promise.all([gt(this.hass),(t=this.hass,vt(t,{type:"ha_soc/permissions/dashboards/list"}).then(t=>t.dashboards))]);this._users=e.filter(t=>t.is_active),this._dashboards=s,void 0===this._selected&&s.length&&(this._selected=s[0].url_path??null),void 0!==this._selected&&await this._loadViews()}finally{this._loading=!1}var t}async _loadViews(){this._viewsError=null;try{const s=await(t=this.hass,e=this._selected??null,vt(t,{type:"ha_soc/permissions/dashboard_config",url_path:e}).then(t=>t.config)),i=s?.views??[];this._views=i.map((t,e)=>({path:t.path??String(e),title:t.title??t.path??`View ${e+1}`,visibleUserIds:Array.isArray(t.visible)?t.visible.map(t=>t.user):null}))}catch(t){this._views=[],this._viewsError="not_found"===t?.code?"This dashboard has no saved layout yet — Home Assistant is showing an auto-generated default until someone opens and customizes it in the dashboard editor. There's nothing here for the permissions matrix to manage until then.":`Could not load this dashboard's views: ${t?.message??t}`}var t,e}async _onSelectDashboard(t){const e=t.target.value;this._selected="__default__"===e?null:e,await this._loadViews()}async _onToggleUser(t,e){const s=t.visibleUserIds??this._users.map(t=>t.id),i=s.includes(e)?s.filter(t=>t!==e):[...s,e],a=i.length===this._users.length?[]:i;await((t,e,s,i)=>vt(t,{type:"ha_soc/permissions/view_visibility/set",url_path:e,view_path:s,user_ids:i}))(this.hass,this._selected??null,t.path,a),await this._loadViews()}async _onToggleFlag(t,e,s){await((t,e,s)=>vt(t,{type:"ha_soc/permissions/dashboard_flags/set",dashboard_id:e,...s}))(this.hass,t,{[e]:s}),await this._load()}async _onCheckDrift(){var t;this._drift=await(t=this.hass,vt(t,{type:"ha_soc/permissions/drift/check"}).then(t=>t.drift))}render(){if(this._loading)return B`<div class="empty">Loading dashboards…</div>`;const t=this._dashboards.find(t=>(t.url_path??null)===(this._selected??null));return B`
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
                    @change=${e=>this._onToggleFlag(t.id,"require_admin",e.target.checked)}
                  />
                  require_admin
                </label>
                <label style="font-size:12.5px;display:flex;align-items:center;gap:4px;">
                  <input
                    type="checkbox"
                    .checked=${!1!==t.show_in_sidebar}
                    @change=${e=>this._onToggleFlag(t.id,"show_in_sidebar",e.target.checked)}
                  />
                  show in sidebar
                </label>
              `:W}
          <span class="spacer"></span>
          <button class="ha-btn" @click=${this._onCheckDrift}>Check drift</button>
        </div>

        ${this._drift.length?B`<p style="font-size:12.5px;color:var(--warning-color);">
              ${this._drift.length} view(s) no longer match the policy last applied here — likely edited directly in the dashboard editor.
            </p>`:W}

        ${this._views.length?B`
              <table>
                <thead>
                  <tr>
                    <th>View</th>
                    ${this._users.map(t=>B`<th>${t.name??t.id}</th>`)}
                  </tr>
                </thead>
                <tbody>
                  ${this._views.map(t=>B`
                      <tr>
                        <td>${t.title}</td>
                        ${this._users.map(e=>{const s=null===t.visibleUserIds||t.visibleUserIds.includes(e.id);return B`
                            <td>
                              <input
                                type="checkbox"
                                .checked=${s}
                                @change=${()=>this._onToggleUser(t,e.id)}
                              />
                            </td>
                          `})}
                      </tr>
                    `)}
                </tbody>
              </table>
            `:B`<div class="empty">
              ${this._viewsError??"This dashboard has no views, or is YAML-managed (read-only)."}
            </div>`}
      </div>
    `}};Rt.styles=Ft,t([pt({attribute:!1})],Rt.prototype,"hass",void 0),t([ut()],Rt.prototype,"_users",void 0),t([ut()],Rt.prototype,"_dashboards",void 0),t([ut()],Rt.prototype,"_selected",void 0),t([ut()],Rt.prototype,"_views",void 0),t([ut()],Rt.prototype,"_loading",void 0),t([ut()],Rt.prototype,"_drift",void 0),t([ut()],Rt.prototype,"_viewsError",void 0),Rt=t([dt("ha-soc-permissions-view")],Rt);const Lt=["new","confirmed","dismissed","resolved"],Ut=["critical","high","medium","low","info"];function Nt(t){const e=Ut.indexOf(t);return-1===e?Ut.length:e}function Dt(t){return"0.0.0.0"===t?{priority:0,label:"all interfaces",cls:"high"}:t?t.startsWith("127.")||t.startsWith("169.254.")?{priority:3,label:"loopback / link-local",cls:"good"}:function(t){const e=t.match(/^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/);if(!e)return!1;const[s,i]=[Number(e[1]),Number(e[2])];return 10===s||172===s&&i>=16&&i<=31||192===s&&168===i}(t)?{priority:2,label:"private (RFC 1918)",cls:"low"}:{priority:1,label:"public / routable",cls:"high"}:{priority:4,label:"unresolved (IPv6)",cls:"info"}}let Ht=class extends rt{constructor(){super(...arguments),this._scannerFindings=[],this._vulnFindings=[],this._misconfigFindings=[],this._probe=null,this._loading=!0,this._scanning=!1,this._firewall=null,this._fwDraftRules=[{action:"allow",proto:"tcp",port:0,source:""}],this._fwBackupAck=!1,this._fwSubmitting=!1,this._fwError=null,this._fwPollHandle=null}connectedCallback(){super.connectedCallback(),this._load()}disconnectedCallback(){super.disconnectedCallback(),null!==this._fwPollHandle&&(window.clearInterval(this._fwPollHandle),this._fwPollHandle=null)}async _load(){this._loading=!0;try{const[e,s,i,a,n]=await Promise.all([(t=this.hass,vt(t,{type:"ha_soc/scanner/list"}).then(t=>t.findings)),bt(this.hass),$t(this.hass),kt(this.hass),St(this.hass)]);this._scannerFindings=e,this._vulnFindings=s,this._misconfigFindings=i.misconfig_findings,this._probe=a,this._firewall=n,this._maybeManageFirewallPolling()}finally{this._loading=!1}var t}_maybeManageFirewallPolling(){const t=null!=this._firewall?.pending;t&&null===this._fwPollHandle?this._fwPollHandle=window.setInterval(()=>this._pollFirewallStatus(),2e3):t||null===this._fwPollHandle||(window.clearInterval(this._fwPollHandle),this._fwPollHandle=null)}async _pollFirewallStatus(){this._applyFirewallStatus(await St(this.hass))}_applyFirewallStatus(t){const e=null!=this._firewall?.pending;this._firewall=t,e&&!t.pending&&(this._fwBackupAck=!1),this._maybeManageFirewallPolling()}_fwRuleValid(t){return Number.isInteger(t.port)&&t.port>=1&&t.port<=65535&&("allow"===t.action||"deny"===t.action)&&("tcp"===t.proto||"udp"===t.proto)}_fwUpdateRule(t,e){this._fwDraftRules=this._fwDraftRules.map((s,i)=>i===t?{...s,...e}:s)}_fwAddRule(){this._fwDraftRules=[...this._fwDraftRules,{action:"allow",proto:"tcp",port:0,source:""}]}_fwRemoveRule(t){this._fwDraftRules=this._fwDraftRules.filter((e,s)=>s!==t)}async _onProposeTest(){this._fwError=null,this._fwSubmitting=!0;try{const t=this._fwDraftRules.map(t=>({action:t.action,proto:t.proto,port:t.port,source:t.source?t.source:null}));await((t,e,s)=>vt(t,{type:"ha_soc/firewall/test",rules:e,backup_acknowledged:s}))(this.hass,t,this._fwBackupAck),this._applyFirewallStatus(await St(this.hass))}catch(t){this._fwError=t?.message??"Failed to propose the firewall change."}finally{this._fwSubmitting=!1}}async _onConfirmTest(){if(this._firewall?.pending){this._fwError=null,this._fwSubmitting=!0;try{await(t=this.hass,e=this._firewall.pending.test_id,vt(t,{type:"ha_soc/firewall/confirm",test_id:e})),this._applyFirewallStatus(await St(this.hass))}catch(t){this._fwError=t?.message??"Failed to confirm the firewall change."}finally{this._fwSubmitting=!1}var t,e}}async _onCancelTest(){if(this._firewall?.pending){this._fwError=null,this._fwSubmitting=!0;try{await(t=this.hass,e=this._firewall.pending.test_id,vt(t,{type:"ha_soc/firewall/cancel",test_id:e})),this._applyFirewallStatus(await St(this.hass))}catch(t){this._fwError=t?.message??"Failed to cancel the firewall change."}finally{this._fwSubmitting=!1}var t,e}}async _onScanIntegrations(){this._scanning=!0;try{await(t=this.hass,vt(t,{type:"ha_soc/scanner/scan_now",domain:e})),await this._load()}finally{this._scanning=!1}var t,e}async _onScanVulns(){this._scanning=!0;try{await(t=this.hass,vt(t,{type:"ha_soc/vulns/scan_now"}).then(t=>t.findings)),await this._load()}finally{this._scanning=!1}var t}async _onVulnStatus(t,e){await((t,e,s,i)=>vt(t,{type:"ha_soc/vulns/set_status",finding_id:e,status:s,note:i}))(this.hass,t,e),await this._load()}async _onMisconfigStatus(t,e){await((t,e,s,i)=>vt(t,{type:"ha_soc/misconfig/set_status",finding_id:e,status:s,note:i}))(this.hass,t,e),await this._load()}_groupedVulnFindings(){const t=new Map;for(const e of this._vulnFindings){const s=String(e.device_name??"Unknown device"),i=t.get(s);i?i.push(e):t.set(s,[e])}const e=Array.from(t.entries()).map(([t,e])=>({device_name:t,findings:[...e].sort((t,e)=>Nt(t.severity)-Nt(e.severity))}));return e.sort((t,e)=>Nt(t.findings[0].severity)-Nt(e.findings[0].severity)),e}_renderStatusSelect(t,e,s){return B`
      <select @change=${t=>s(t.target.value)}>
        ${Lt.map(t=>B`<option value=${t} ?selected=${t===e}>${t}</option>`)}
      </select>
    `}render(){return this._loading?B`<div class="empty">Loading findings…</div>`:B`
      <div class="card">
        <h3>Misconfiguration Findings</h3>
        ${this._misconfigFindings.length?B`
              <table>
                <thead>
                  <tr>
                    <th>Check</th>
                    <th>Summary</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  ${this._misconfigFindings.map(t=>B`
                      <tr>
                        <td><span class="pill ${t.severity}"><span class="dot"></span>${t.check}</span></td>
                        <td>${t.summary}</td>
                        <td>${this._renderStatusSelect(t.id,t.status,e=>this._onMisconfigStatus(t.id,e))}</td>
                      </tr>
                    `)}
                </tbody>
              </table>
            `:B`<div class="empty">No findings.</div>`}
      </div>

      <div class="card">
        <h3>Integration Security Scanner</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Static AST/regex analysis of every installed integration's source — core and
          custom. Every finding is advisory and needs a human to confirm; Home
          Assistant's own quality tooling (hassfest) never checks for these patterns and
          never runs against custom_components at all.
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
                    <th>Domain</th>
                    <th>Pattern</th>
                    <th>Location</th>
                    <th>Confidence</th>
                    <th>CWE</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  ${this._scannerFindings.map(t=>B`
                      <tr>
                        <td>${t.domain}</td>
                        <td><span class="pill ${t.severity}"><span class="dot"></span>${t.pattern}</span></td>
                        <td>${t.file}:${t.line}</td>
                        <td>${t.confidence}</td>
                        <td>${t.cwe}</td>
                        <td>${this._renderStatusSelect(t.id,t.status,e=>this._onVulnStatus(t.id,e))}</td>
                      </tr>
                    `)}
                </tbody>
              </table>
            `:B`<div class="empty">No findings.</div>`}
      </div>

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
                    <th>CVE</th>
                    <th>CVSS</th>
                    <th>Confidence</th>
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

      ${this._renderProbeCard()}
      ${this._renderFirewallCard()}
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
    `}_renderPortsByBindAddress(t){const e=new Map;for(const s of t){const t=s.address??"__unresolved__",i=e.get(t);i?i.push(s):e.set(t,[s])}const s=Array.from(e.entries()).sort((t,e)=>{const s=Dt("__unresolved__"===t[0]?null:t[0]),i=Dt("__unresolved__"===e[0]?null:e[0]);return s.priority!==i.priority?s.priority-i.priority:t[0].localeCompare(e[0])});return B`
      <table>
        <thead>
          <tr>
            <th>Port</th>
            <th>Protocol</th>
            <th>Interface</th>
          </tr>
        </thead>
        ${s.map(([t,e])=>{const s="__unresolved__"===t?null:t,i=Dt(s);return B`
            <tbody>
              <tr>
                <td colspan="3" style="background:rgba(var(--rgb-primary-text-color,0,0,0),0.04);">
                  <strong>${s??"unresolved (IPv6)"}</strong>
                  <span class="pill ${i.cls}" style="margin-left:8px;"
                    ><span class="dot"></span>${i.label}</span
                  >
                  <span class="muted" style="margin-left:8px;font-size:12px;"
                    >${e.length} port${1===e.length?"":"s"}</span
                  >
                </td>
              </tr>
              ${e.slice().sort((t,e)=>t.port-e.port).map(t=>B`
                    <tr>
                      <td>${t.port}</td>
                      <td>${t.proto}</td>
                      <td>
                        ${"(all interfaces)"===t.interface?B`<span class="pill high"><span class="dot"></span>all interfaces</span>`:B`<span class="muted">${t.interface??"—"}</span>`}
                      </td>
                    </tr>
                  `)}
            </tbody>
          `})}
      </table>
    `}_renderFirewallCard(){const t=this._probe,e=this._firewall;return t?.supervisor&&t?.installed&&e?B`
      <div class="card">
        <h3>Firewall Rules</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Reads, and — if you propose a change — writes the host's firewall via the HA
          SOC Probe add-on's <code>NET_ADMIN</code> capability. Every proposed change is
          backed up first and applied to a dedicated chain this project owns outright,
          never the host's raw INPUT chain. An unconfirmed change reverts itself
          automatically once its test window closes.
        </p>

        <h4 class="fw-subhead">Active rules</h4>
        ${e.known_rules&&e.known_rules.length?B`
              <table>
                <thead>
                  <tr>
                    <th>Action</th>
                    <th>Protocol</th>
                    <th>Port</th>
                    <th>Source</th>
                  </tr>
                </thead>
                <tbody>
                  ${e.known_rules.map(t=>B`
                      <tr>
                        <td>
                          <span class="pill ${"allow"===t.action?"good":"critical"}"
                            ><span class="dot"></span>${t.action}</span
                          >
                        </td>
                        <td>${t.proto}</td>
                        <td>${t.port}</td>
                        <td class="muted">${t.source??"any"}</td>
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
        ${e.pending?this._renderFirewallPending(e.pending):this._renderFirewallBuilder()}
        ${this._fwError?B`<p style="color:var(--error-color,#db4437);font-size:12.5px;margin-top:10px;">${this._fwError}</p>`:W}
      </div>
    `:W}_renderFirewallPending(t){const e=Math.max(0,Math.round((new Date(t.expires_at).getTime()-Date.now())/1e3)),s={testing:t.applied_at?"Testing — live on the host":"Queued — waiting for the add-on to apply",confirmed:"Confirmed — waiting for the add-on to acknowledge",reverted:"Reverting — waiting for the add-on to acknowledge",expired:"Window expired — reverting automatically"};return B`
      <h4 class="fw-subhead">Proposed rules — ${s[t.status]??t.status}</h4>
      <table>
        <thead>
          <tr>
            <th>Action</th>
            <th>Protocol</th>
            <th>Port</th>
            <th>Source</th>
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
      </div>
    `}_renderFirewallBuilder(){const t=this._fwBackupAck&&this._fwDraftRules.length>0&&this._fwDraftRules.every(t=>this._fwRuleValid(t));return B`
      <h4 class="fw-subhead">Propose a change</h4>
      <table>
        <thead>
          <tr>
            <th>Action</th>
            <th>Protocol</th>
            <th>Port</th>
            <th>Source (optional)</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          ${this._fwDraftRules.map((t,e)=>B`
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
                    placeholder="e.g. 192.168.10.0/24"
                    .value=${t.source??""}
                    style="width:170px;"
                    @input=${t=>this._fwUpdateRule(e,{source:t.target.value})}
                  />
                </td>
                <td><button class="ha-btn danger" @click=${()=>this._fwRemoveRule(e)}>Remove</button></td>
              </tr>
            `)}
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
        <button class="ha-btn" ?disabled=${!t||this._fwSubmitting} @click=${this._onProposeTest}>
          Test
        </button>
      </div>
    `}};Ht.styles=Ft,t([pt({attribute:!1})],Ht.prototype,"hass",void 0),t([ut()],Ht.prototype,"_scannerFindings",void 0),t([ut()],Ht.prototype,"_vulnFindings",void 0),t([ut()],Ht.prototype,"_misconfigFindings",void 0),t([ut()],Ht.prototype,"_probe",void 0),t([ut()],Ht.prototype,"_loading",void 0),t([ut()],Ht.prototype,"_scanning",void 0),t([ut()],Ht.prototype,"_firewall",void 0),t([ut()],Ht.prototype,"_fwDraftRules",void 0),t([ut()],Ht.prototype,"_fwBackupAck",void 0),t([ut()],Ht.prototype,"_fwSubmitting",void 0),t([ut()],Ht.prototype,"_fwError",void 0),Ht=t([dt("ha-soc-scanner-view")],Ht);function Ot(t,e){t.dispatchEvent(new CustomEvent("ha-soc-navigate",{detail:{tab:e},bubbles:!0,composed:!0}))}function Tt(t){window.history.pushState(null,"",t),window.dispatchEvent(new CustomEvent("location-changed",{bubbles:!0,composed:!0}))}function Mt(t){return`/config/devices/dashboard?historyBack=1&config_entry=${t}`}const Vt={lock:"Locks",siren:"Sirens",valve:"Valves"},Bt=[{key:"available",label:"Available"},{key:"partial",label:"Partial"},{key:"unavailable",label:"Unavailable"},{key:"disabled",label:"Disabled"},{key:"no_entities",label:"No Entities"}],jt=["critical","high","medium","low"],Wt={failing:"Failing",credential:"Credential issue",communication:"Communication issue",collection:"Collection issue",errors:"Logging errors",debug_logging:"Debug logging enabled",disabled:"Disabled"},qt={failing:{label:"Unavailable",colorVar:"var(--status-critical)"},credential:{label:"Unavailable",colorVar:"var(--status-critical)"},communication:{label:"Unavailable",colorVar:"var(--status-critical)"},collection:{label:"Unavailable",colorVar:"var(--status-critical)"},errors:{label:"Warning",colorVar:"var(--status-warning)"},debug_logging:{label:"Warning",colorVar:"var(--status-warning)"},disabled:{label:"Disabled",colorVar:"var(--cat-other)"}},Gt=[20,50,100,"all"],Kt=[20,50,100,"all"];let Yt=class extends rt{constructor(){super(...arguments),this._summary=null,this._deviceOverview=null,this._integrationOverview=null,this._peripherals=null,this._security=null,this._detections=[],this._risk={},this._users=[],this._loading=!0,this._deviceSearch="",this._deviceStatusFilter=null,this._deviceSort={key:"risk_score",dir:"desc"},this._devicePageSize=20,this._integrationSearch="",this._integrationPageSize=20}connectedCallback(){super.connectedCallback(),this._load()}updated(){this.classList.toggle("dark",!!this.hass?.themes?.darkMode)}async _load(){this._loading=!0;try{const[e,s,i,a,n,o,r,l]=await Promise.all([(t=this.hass,vt(t,{type:"ha_soc/dashboard/summary"})),wt(this.hass),xt(this.hass),At(this.hass),Pt(this.hass),yt(this.hass),_t(this.hass),gt(this.hass)]);this._summary=e,this._deviceOverview=s,this._integrationOverview=i,this._peripherals=a,this._security=n,this._detections=o,this._risk=r,this._users=l}finally{this._loading=!1}var t}async _onAck(t){await mt(this.hass,t,"ack"),await this._load()}async _onResolve(t){await mt(this.hass,t,"resolved"),await this._load()}_nameFor(t){return t?this._users.find(e=>e.id===t)?.name??t:"unknown"}_goto(t){Ot(this,t)}_donutGradient(t){const e=t.reduce((t,e)=>t+e.value,0)||1;let s=0;const i=t.map(t=>{const i=s/e*100;s+=t.value;const a=s/e*100;return`${t.color} ${i}% ${a}%`});return`conic-gradient(${i.join(", ")})`}_onSort(t){this._deviceSort=this._deviceSort.key===t?{key:t,dir:"asc"===this._deviceSort.dir?"desc":"asc"}:{key:t,dir:"name"===t||"vendor"===t?"asc":"desc"}}_onStatusTileClick(t){this._deviceStatusFilter=this._deviceStatusFilter===t?null:t,this.renderRoot.querySelector("#devices-card")?.scrollIntoView({behavior:"smooth",block:"start"})}_sortedFilteredDevices(){const t=this._deviceOverview?.devices??[],e=this._deviceSearch.trim().toLowerCase(),s=t.filter(t=>(!this._deviceStatusFilter||t.status===this._deviceStatusFilter)&&(!e||(t.name.toLowerCase().includes(e)||t.vendor.toLowerCase().includes(e)||t.os.toLowerCase().includes(e)))),{key:i,dir:a}=this._deviceSort,n=[...s].sort((t,e)=>{const s=t[i],n=e[i],o="string"==typeof s?s.localeCompare(n):s-n;return"asc"===a?o:-o});return n}_filteredIntegrations(){const t=this._integrationOverview?.integrations??[],e=this._integrationSearch.trim().toLowerCase();return e?t.filter(t=>t.title.toLowerCase().includes(e)||t.domain.toLowerCase().includes(e)):t}_statusDotColor(t){switch(t){case"unavailable":return"var(--status-critical)";case"partial":return"var(--status-warning)";case"disabled":return"var(--cat-other)";case"no_entities":return"var(--primary-color)";default:return"var(--status-good)"}}render(){if(this._loading||!this._summary||!this._deviceOverview||!this._integrationOverview)return B`<div class="empty">Loading dashboard…</div>`;const t=this._summary,e=this._deviceOverview,s=this._integrationOverview,i=this._detections.filter(t=>"open"===t.status),a=e.devices.reduce((t,e)=>(t.critical+=e.severity_counts.critical,t.high+=e.severity_counts.high,t.medium+=e.severity_counts.medium,t.low+=e.severity_counts.low,t),{critical:0,high:0,medium:0,low:0}),n=a.critical+a.high+a.medium+a.low,o=[{key:"critical",label:"Critical",color:"var(--status-critical)",value:a.critical},{key:"high",label:"High",color:"var(--status-serious)",value:a.high},{key:"medium",label:"Medium",color:"var(--status-warning)",value:a.medium},{key:"low",label:"Low",color:"var(--status-good)",value:a.low}],r=Math.max(0,Math.min(100,e.combined_risk_score/10*100)),l=t.entity_state_counts??{unavailable:0,unknown:0},d=l.unavailable+l.unknown,c=[{key:"unavailable",label:"Failed (unavailable)",color:"var(--status-critical)",value:l.unavailable},{key:"unknown",label:"Unknown",color:"var(--status-warning)",value:l.unknown}],h=this._sortedFilteredDevices(),p="all"===this._devicePageSize?h:h.slice(0,this._devicePageSize),u=this._filteredIntegrations(),v="all"===this._integrationPageSize?u:u.slice(0,this._integrationPageSize),g=[{key:"low",color:"var(--status-good)",value:t.risk_band_counts.low??0},{key:"moderate",color:"var(--status-warning)",value:t.risk_band_counts.moderate??0},{key:"high",color:"var(--status-serious)",value:t.risk_band_counts.high??0},{key:"critical",color:"var(--status-critical)",value:t.risk_band_counts.critical??0}],_=[{key:"enabled",color:"var(--cat-1)",value:t.mfa_counts.enabled},{key:"disabled",color:"var(--cat-2)",value:t.mfa_counts.disabled}],y=[{key:"critical",color:"var(--status-critical)",value:t.detection_severity_counts.critical??0},{key:"high",color:"var(--status-serious)",value:t.detection_severity_counts.high??0},{key:"medium",color:"var(--status-warning)",value:t.detection_severity_counts.medium??0},{key:"low",color:"var(--status-good)",value:t.detection_severity_counts.low??0}];return B`
      ${this._renderSecurityCard()}

      <h2 class="section-title">Device &amp; Vulnerability Overview</h2>
      <div class="row3">
        <div class="card device-status-card">
          <h3>Device Status</h3>
          <div class="status-tiles">
            ${Bt.map(t=>B`
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
          <h3>Vulnerability Count by Severity</h3>
          <div class="donut-wrap">
            <div class="donut" style="background:${this._donutGradient(o)}">
              <div class="center">${n.toLocaleString()}</div>
            </div>
            <div class="legend">
              ${o.map(t=>B`
                  <div class="row">
                    <span class="sw" style="background:${t.color}"></span>${t.label}
                    <span class="val">${t.value.toLocaleString()}</span>
                  </div>
                `)}
            </div>
          </div>
        </div>

        <div class="card gauge-card clickable" @click=${()=>this._goto("scanner")} title="View vulnerability findings">
          <h3>Risk Score</h3>
          <div class="gauge-value">${e.combined_risk_score.toFixed(1)}</div>
          <div class="gauge-track">
            <div class="gauge-marker" style="left:${r}%"></div>
          </div>
          <div class="gauge-caption">
            Combined risk score of all devices — weighted so higher-severity CVEs count more.
          </div>
        </div>

        <div class="card clickable" @click=${()=>this._goto("entity_remap")} title="Fix broken entity references">
          <h3>Failed / Unknown Entities</h3>
          <div class="donut-wrap">
            <div class="donut" style="background:${this._donutGradient(c)}">
              <div class="center">${d.toLocaleString()}</div>
            </div>
            <div class="legend">
              ${c.map(t=>B`
                  <div class="row">
                    <span class="sw" style="background:${t.color}"></span>${t.label}
                    <span class="val">${t.value.toLocaleString()}</span>
                  </div>
                `)}
            </div>
          </div>
        </div>
      </div>

      <h2 class="section-title">Users &amp; Detections</h2>
      <div class="donuts-row">
        <div class="card clickable" @click=${()=>this._goto("users")} title="View users">
          <h3>Users by Risk Band</h3>
          <div class="donut-wrap">
            <div class="donut" style="background:${this._donutGradient(g)}">
              <div class="center">${t.total_users_count}</div>
            </div>
            <div class="legend">
              ${g.map(t=>B`
                  <div class="row">
                    <span class="sw" style="background:${t.color}"></span>${t.key}
                    <span class="val">${t.value}</span>
                  </div>
                `)}
            </div>
          </div>
        </div>

        <div class="card clickable" @click=${()=>this._goto("users")} title="View users">
          <h3>MFA Adoption</h3>
          <div class="donut-wrap">
            <div class="donut" style="background:${this._donutGradient(_)}">
              <div class="center">
                ${t.mfa_counts.enabled+t.mfa_counts.disabled>0?`${Math.round(t.mfa_counts.enabled/(t.mfa_counts.enabled+t.mfa_counts.disabled)*100)}%`:"—"}
              </div>
            </div>
            <div class="legend">
              <div class="row"><span class="sw" style="background:var(--cat-1)"></span>Enabled<span class="val">${t.mfa_counts.enabled}</span></div>
              <div class="row"><span class="sw" style="background:var(--cat-2)"></span>No MFA<span class="val">${t.mfa_counts.disabled}</span></div>
            </div>
          </div>
        </div>

        <div class="card clickable" @click=${()=>this._goto("audit")} title="View audit / detections">
          <h3>Detections by Severity</h3>
          <div class="donut-wrap">
            <div class="donut" style="background:${this._donutGradient(y)}">
              <div class="center">${this._detections.length}</div>
            </div>
            <div class="legend">
              ${y.map(t=>B`
                  <div class="row">
                    <span class="sw" style="background:${t.color}"></span>${t.key}
                    <span class="val">${t.value}</span>
                  </div>
                `)}
            </div>
          </div>
        </div>
      </div>

      <div class="card">
        <h3>Recent suspicious activity</h3>
        ${i.length?B`
              <table>
                <thead>
                  <tr>
                    <th>Time</th>
                    <th>Rule</th>
                    <th>Severity</th>
                    <th>User</th>
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
            `:B`<div class="empty">No open detections.</div>`}
      </div>

      <h2 class="section-title">Devices &amp; Integrations</h2>
      <div class="row2">
        <div class="card" id="devices-card">
          <h3>All Devices</h3>
          ${this._deviceStatusFilter?B`
                <div class="filter-chip" @click=${()=>this._deviceStatusFilter=null}>
                  ${Bt.find(t=>t.key===this._deviceStatusFilter)?.label} ✕
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
          ${0===h.length?B`<div class="empty">No devices found.</div>`:B`
                <div style="overflow-x:auto;">
                  <table>
                    <thead>
                      <tr>
                        <th>Health</th>
                        <th class="sortable" @click=${()=>this._onSort("name")}>
                          Device${this._sortArrow("name")}
                        </th>
                        <th class="sortable" @click=${()=>this._onSort("vendor")}>
                          Vendor${this._sortArrow("vendor")}
                        </th>
                        <th class="sortable" @click=${()=>this._onSort("risk_score")}>
                          Risk Score${this._sortArrow("risk_score")}
                        </th>
                        <th class="sortable" @click=${()=>this._onSort("total_findings")}>
                          Total${this._sortArrow("total_findings")}
                        </th>
                        <th>Severity</th>
                      </tr>
                    </thead>
                    <tbody>
                      ${p.map(t=>B`
                          <tr
                            class="clickable"
                            title="Open in Home Assistant's Devices page"
                            @click=${()=>Tt(`/config/devices/device/${t.device_id}`)}
                          >
                            <td><span class="health-dot" style="background:${this._statusDotColor(t.status)}"></span></td>
                            <td>${t.name}</td>
                            <td class="muted">${t.vendor}</td>
                            <td class="num">${t.risk_score.toFixed(1)}</td>
                            <td class="num">${t.total_findings}</td>
                            <td>
                              <span class="sev-cell">
                                ${jt.map(e=>B`
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
                    >Showing ${p.length} of ${h.length} device${1===h.length?"":"s"}</span
                  >
                  <select
                    .value=${String(this._devicePageSize)}
                    @change=${t=>{const e=t.target.value;this._devicePageSize="all"===e?"all":Number(e)}}
                  >
                    ${Gt.map(t=>B`
                        <option value=${String(t)} ?selected=${t===this._devicePageSize}>
                          ${"all"===t?"Show all":`Show ${t}`}
                        </option>
                      `)}
                  </select>
                </div>
              `}
        </div>

        <div class="card">
          <h3>Issues by Integration</h3>
          ${0===s.integrations.length?B`<div class="empty">No integration issues detected.</div>`:B`
                <div class="devices-toolbar">
                  <input
                    type="text"
                    placeholder="Search integrations…"
                    .value=${this._integrationSearch}
                    @input=${t=>this._integrationSearch=t.target.value}
                  />
                </div>
                ${0===u.length?B`<div class="empty">No integration matches "${this._integrationSearch}".</div>`:B`
                      <div style="overflow-x:auto;">
                        <table>
                          <thead>
                            <tr>
                              <th>Integration</th>
                              <th>Severity</th>
                            </tr>
                          </thead>
                          <tbody>
                            ${v.map(t=>{const e=qt[t.issue_category];return B`
                                <tr
                                  class="clickable"
                                  title="${t.title} — ${Wt[t.issue_category]}. Open in Home Assistant's Devices page"
                                  @click=${()=>Tt(Mt(t.entry_id))}
                                >
                                  <td>${t.title}</td>
                                  <td>
                                    <span class="sev-cell">
                                      <span class="sev-dot" style="background:${e.colorVar}"></span>
                                      ${e.label}
                                      <span class="num">${t.error_count_24h}</span>
                                    </span>
                                  </td>
                                </tr>
                              `})}
                          </tbody>
                        </table>
                      </div>
                      <div class="devices-footer">
                        <span
                          >Showing ${v.length} of ${u.length} integration${1===u.length?"":"s"}</span
                        >
                        <select
                          .value=${String(this._integrationPageSize)}
                          @change=${t=>{const e=t.target.value;this._integrationPageSize="all"===e?"all":Number(e)}}
                        >
                          ${Kt.map(t=>B`
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
    `}_sortArrow(t){return this._deviceSort.key!==t?W:B`<span class="arrow">${"asc"===this._deviceSort.dir?"▲":"▼"}</span>`}_renderSecurityCard(){const t=this._security;if(!t)return W;const e={};for(const s of t.entities)(e[s.domain]??=[]).push(s);return B`
      <div class="card">
        <h3>
          Security Integrations Health
          ${t.problem_count||t.low_battery_count?B`<span class="tag" style="background:rgba(219,68,55,0.15);color:var(--error-color,#db4437);">
                ${t.problem_count} problem${1===t.problem_count?"":"s"}, ${t.low_battery_count} low
                battery
              </span>`:B`<span class="tag enforced">all clear</span>`}
        </h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Every lock/siren/valve entity regardless of integration, plus local USB/serial
          peripherals. The curated security-integration health list (Kidde, Elk-M1, UniFi
          Protect, Keymaster, Emporia Vue) moved to Settings — configurable there too.
        </p>
        <div class="security-health-grid">
          ${Object.entries(Vt).filter(([e])=>t.sources_enabled[e]??!0).map(([t,s])=>{const i=e[t]??[],a=i.filter(t=>t.problem).length,n=i.filter(t=>t.low_battery).length;return B`
                <div
                  class="security-source-tile ${i.length?"clickable":""}"
                  title=${i.length?`View ${s.toLowerCase()} in Home Assistant's Devices page`:""}
                  @click=${()=>i.length&&Tt(function(t){return`/config/devices/dashboard?historyBack=1&domain=${t}`}(t))}
                >
                  <div class="label">${s}</div>
                  <div class="value" style="color:${a?"var(--error-color,#db4437)":"inherit"}">
                    ${a}
                  </div>
                  <div class="sub">
                    ${i.length} total${n?`, ${n} low battery`:""}
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
    `:W}};Yt.styles=[Ft,o`
      h2.section-title {
        font-size: 13px;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        color: var(--secondary-text-color);
        margin: 28px 0 12px;
        font-weight: 600;
      }
      h2.section-title:first-child {
        margin-top: 0;
      }

      .row3 {
        display: grid;
        grid-template-columns: 1.3fr 1fr 1fr 1fr;
        gap: 12px;
        margin-bottom: 16px;
      }
      .row2 {
        display: grid;
        grid-template-columns: 1.4fr 1fr;
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
        background: var(--status-warning);
        color: #3a2900;
      }
      .status-tile.unavailable {
        background: var(--status-critical);
        color: #fff;
      }
      .status-tile.disabled {
        background: var(--cat-other);
        color: #fff;
      }
      .status-tile.no_entities {
        background: var(--primary-color);
        color: #fff;
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

      /* -- Donut ----------------------------------------------------------- */
      .donut-wrap {
        display: flex;
        align-items: center;
        gap: 14px;
      }
      .donut {
        width: 100px;
        height: 100px;
        border-radius: 50%;
        position: relative;
        flex: none;
      }
      .donut::after {
        content: "";
        position: absolute;
        inset: 22%;
        border-radius: 50%;
        background: var(--card-background-color, #fff);
      }
      .donut .center {
        position: absolute;
        inset: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        font-size: 18px;
        z-index: 1;
      }
      .legend {
        font-size: 12px;
        display: flex;
        flex-direction: column;
        gap: 6px;
        flex: 1;
        min-width: 0;
      }
      .legend .row {
        display: flex;
        align-items: center;
        gap: 6px;
      }
      .legend .sw {
        width: 9px;
        height: 9px;
        border-radius: 2px;
        flex: none;
      }
      .legend .val {
        margin-left: auto;
        font-weight: 700;
        font-variant-numeric: tabular-nums;
      }

      /* -- Risk gauge ------------------------------------------------------ */
      .gauge-card .gauge-value {
        font-size: 30px;
        font-weight: 700;
        margin-bottom: 10px;
      }
      .gauge-track {
        position: relative;
        height: 12px;
        border-radius: 6px;
        background: linear-gradient(
          90deg,
          var(--status-good) 0%,
          var(--status-warning) 40%,
          var(--status-serious) 70%,
          var(--status-critical) 100%
        );
      }
      .gauge-marker {
        position: absolute;
        top: -10px;
        width: 0;
        height: 0;
        border-left: 7px solid transparent;
        border-right: 7px solid transparent;
        border-top: 9px solid var(--primary-text-color);
        transform: translateX(-50%);
      }
      .gauge-caption {
        margin-top: 10px;
        font-size: 11.5px;
        color: var(--secondary-text-color);
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
      th.sortable {
        cursor: pointer;
        user-select: none;
      }
      th.sortable .arrow {
        opacity: 0.6;
        margin-left: 3px;
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
        gap: 12px;
        margin-top: 8px;
      }
      .security-source-tile {
        border: 1px solid var(--divider-color);
        border-radius: 8px;
        padding: 10px 12px;
      }
      .security-source-tile .label {
        font-size: 12px;
        color: var(--secondary-text-color);
        margin-bottom: 4px;
      }
      .security-source-tile .value {
        font-size: 20px;
        font-weight: 700;
      }
      .security-source-tile .sub {
        font-size: 11px;
        color: var(--secondary-text-color);
        margin-top: 2px;
      }
    `],t([pt({attribute:!1})],Yt.prototype,"hass",void 0),t([ut()],Yt.prototype,"_summary",void 0),t([ut()],Yt.prototype,"_deviceOverview",void 0),t([ut()],Yt.prototype,"_integrationOverview",void 0),t([ut()],Yt.prototype,"_peripherals",void 0),t([ut()],Yt.prototype,"_security",void 0),t([ut()],Yt.prototype,"_detections",void 0),t([ut()],Yt.prototype,"_risk",void 0),t([ut()],Yt.prototype,"_users",void 0),t([ut()],Yt.prototype,"_loading",void 0),t([ut()],Yt.prototype,"_deviceSearch",void 0),t([ut()],Yt.prototype,"_deviceStatusFilter",void 0),t([ut()],Yt.prototype,"_deviceSort",void 0),t([ut()],Yt.prototype,"_devicePageSize",void 0),t([ut()],Yt.prototype,"_integrationSearch",void 0),t([ut()],Yt.prototype,"_integrationPageSize",void 0),Yt=t([dt("ha-soc-dashboard-view")],Yt);const Zt=[25,50,100,"all"];let Jt=class extends rt{constructor(){super(...arguments),this._overview=null,this._loading=!0,this._error=null,this._clientSearch="",this._clientPage=0,this._clientPageSize=25,this._clientVlanFilter="",this._clientSsidFilter="",this._deviceSearch="",this._devicePage=0,this._devicePageSize=25}connectedCallback(){super.connectedCallback(),this._load()}async _load(){this._loading=!0,this._error=null;try{this._overview=await(t=this.hass,vt(t,{type:"ha_soc/network/overview"}))}catch(t){this._error=t instanceof Error?t.message:String(t),this._overview=null}finally{this._loading=!1}var t}_fmtBytes(t){if(null==t)return"—";if(t<1024)return`${t} B`;const e=["KB","MB","GB","TB","PB"];let s=t/1024,i=0;for(;s>=1024&&i<e.length-1;)s/=1024,i++;return`${s.toFixed(s>=100?0:1)} ${e[i]}`}_fmtRate(t){if(null==t)return"—";const e=8*t;if(e<1e3)return`${e} bps`;const s=["kbps","Mbps","Gbps"];let i=e/1e3,a=0;for(;i>=1e3&&a<s.length-1;)i/=1e3,a++;return`${i.toFixed(i>=100?0:1)} ${s[a]}`}_fmtBandwidth(t){return t?`↓ ${this._fmtBytes(t.rx_bytes)} · ↑ ${this._fmtBytes(t.tx_bytes)}`:"—"}_fmtUptime(t){if(null==t)return"—";const e=Math.floor(t/86400),s=Math.floor(t%86400/3600),i=Math.floor(t%3600/60);return e>0?`${e}d ${s}h`:s>0?`${s}h ${i}m`:`${i}m`}_fmtLastSeen(t){if(null==t)return"—";const e=Date.now()/1e3,s=Math.max(0,e-t);return s<60?"just now":s<3600?`${Math.floor(s/60)}m ago`:s<86400?`${Math.floor(s/3600)}h ago`:s<2592e3?`${Math.floor(s/86400)}d ago`:new Date(1e3*t).toLocaleDateString()}_fmtVlan(t){return null==t||""===t?"—":String(t)}_renderMatch(t){const e=t.integration_match;if(!e)return B`<span class="muted">—</span>`;const s=e.failing?"failing":e.healthy?"healthy":"other",i=e.failing?"⚠":e.healthy?"●":"○",a=`${e.domain} — config entry state: ${e.state}. Click to open in Home Assistant.`;return B`
      <span
        class="match ${s}"
        title=${a}
        @click=${()=>Tt(Mt(e.entry_id))}
      >
        ${i} ${e.domain}${e.failing?" failing":""}
      </span>
    `}_filter(t,e){const s=e.trim().toLowerCase();return s?t.filter(t=>[t.name,t.ipv4,t.ipv6,t.mac,t.ssid,t.integration_match?.domain].filter(Boolean).some(t=>String(t).toLowerCase().includes(s))):t}_paginate(t,e,s){return"all"===s?t:t.slice(e*s,e*s+s)}render(){if(this._loading)return B`<div class="empty">Loading network…</div>`;if(this._error)return B`<div class="alert">Could not load the Network overview: ${this._error}</div>`;const t=this._overview;return t?t.configured?t.reachable?B`
      ${this._renderFailingBanner(t)} ${this._renderStats(t)} ${this._renderSsid(t)}
      ${this._renderClientsTable(t)} ${this._renderDevicesTable(t)} ${this._renderAcl(t.acl)}
      ${this._renderProtectCard(t)}
      <div class="footer">
        <span>Last updated ${new Date(t.generated_at).toLocaleTimeString()}</span>
        <button class="ha-btn" style="margin-left:auto;" @click=${()=>this._load()}>
          Refresh
        </button>
      </div>
    `:B`
        <div class="alert">
          <strong>UniFi Network is configured but not reachable.</strong><br />
          ${t.error??"Unknown error."}
        </div>
        <button class="ha-btn" @click=${()=>this._load()}>Retry</button>
        ${this._renderProtectCard(t)}
      `:B`
        <div class="card">
          <h3>UniFi Network not configured</h3>
          <p class="muted" style="font-size:13px;line-height:1.6;">
            Add a UniFi Network controller host and a local API key in
            <strong>Settings</strong> (owner only) to see status, WAN throughput,
            wireless clients, and the client / device tables here. The API key is a
            local one generated on the console under
            <em>Settings → Control Plane → Integrations</em>; nothing leaves your LAN.
          </p>
          <button class="ha-btn" @click=${()=>Ot(this,"settings")}>
            Open Settings
          </button>
        </div>
        ${this._renderProtectCard(t)}
      `:B`<div class="empty">No network data.</div>`}_renderFailingBanner(t){return t.failing_endpoint_count?B`
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
    `}_colHeaders(t={}){return B`
      <tr>
        <th>${t.model?"Device":"Client"}</th>
        <th>IPv4</th>
        <th>IPv6</th>
        <th>MAC</th>
        <th class="num">VLAN</th>
        <th>SSID</th>
        ${t.model?B`<th>Model</th>`:W}
        <th class="num">Uptime</th>
        <th>Bandwidth</th>
        <th>Last Seen</th>
        <th>Integration</th>
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
    `}_renderClientsTable(t){const e=Array.from(new Set(t.clients.map(t=>null==t.vlan||""===t.vlan?null:String(t.vlan)).filter(Boolean))).sort((t,e)=>Number(t)-Number(e)),s=Array.from(new Set(t.clients.map(t=>t.ssid).filter(Boolean))).sort();let i=this._filter(t.clients,this._clientSearch);this._clientVlanFilter&&(i=i.filter(t=>String(t.vlan??"")===this._clientVlanFilter)),this._clientSsidFilter&&(i=i.filter(t=>t.ssid===this._clientSsidFilter));const a=this._paginate(i,this._clientPage,this._clientPageSize);return B`
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
    `}_renderDevicesTable(t){const e=this._filter(t.devices,this._deviceSearch),s=this._paginate(e,this._devicePage,this._devicePageSize);return B`
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
                      <th>Device</th>
                      <th>IPv4</th>
                      <th>MAC</th>
                      <th class="num">VLAN</th>
                      <th>Model</th>
                      <th>Firmware</th>
                      <th>Bandwidth</th>
                      <th>Last Seen</th>
                      <th>Integration</th>
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
    `}_aclActionClass(t){const e=(t??"").toLowerCase();return["allow","accept","permit"].some(t=>e.includes(t))?"healthy":["deny","drop","block","reject"].some(t=>e.includes(t))?"failing":"other"}_renderAcl(t){return B`
      <div class="card" id="acl-card">
        <h3>
          ACL Rules — Security Audit
          <span class="muted" style="font-weight:400;font-size:12px;"
            >— order matters; rules are evaluated top to bottom${t.endpoint?` · source: ${t.endpoint}`:""}</span
          >
        </h3>
        ${t.available?t.rules.length?B`
                <div class="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th class="num">#</th>
                        <th>Name</th>
                        <th>Action</th>
                        <th>Networks</th>
                        <th>Direction</th>
                        <th>Protocol</th>
                        <th>Enabled</th>
                      </tr>
                    </thead>
                    <tbody>
                      ${t.rules.map((t,e)=>B`
                          <tr>
                            <td class="num">${t.order??e+1}</td>
                            <td style="font-weight:600;">${t.name??"—"}</td>
                            <td>
                              ${t.action?B`<span class="match ${this._aclActionClass(t.action)}" style="cursor:default;"
                                    >${t.action}</span
                                  >`:B`<span class="muted">—</span>`}
                            </td>
                            <td>
                              ${t.networks.length?B`<span class="chips"
                                    >${t.networks.map(t=>B`<span class="chip">${t}</span>`)}</span
                                  >`:B`<span class="muted">any / —</span>`}
                            </td>
                            <td>${t.direction??"—"}</td>
                            <td>${t.protocol??"—"}</td>
                            <td>
                              ${null==t.enabled?B`<span class="muted">—</span>`:t.enabled?"yes":B`<span class="muted">disabled</span>`}
                            </td>
                          </tr>
                        `)}
                    </tbody>
                  </table>
                </div>
                <div class="note">
                  Order reflects evaluation precedence as returned by the controller. A
                  later "deny" cannot override an earlier "allow" for the same traffic —
                  read top-down when auditing.
                </div>
              `:B`<div class="empty">No ACL rules configured (endpoint: ${t.endpoint}).</div>`:B`
              <div class="note" style="font-size:13px;">
                This controller's Integration API didn't return ACL / firewall rules.
                Endpoints tried:
                <code>${t.endpoints_tried.join(", ")||"—"}</code>.${t.error?B` Last response: ${t.error}.`:""}
                If your controller exposes them under a different path, tell me and I'll
                add it — the field mappings here are marked <code>VERIFY</code> in
                <code>unifi.py</code>.
              </div>
            `}
      </div>
    `}_renderPager(t,e,s,i,a){const n="all"===s?1:Math.max(1,Math.ceil(t/s));return B`
      <div class="footer">
        <button class="ha-btn" ?disabled=${e<=0} @click=${()=>i(e-1)}>Prev</button>
        <span>Page ${e+1} of ${n}</span>
        <button class="ha-btn" ?disabled=${e>=n-1} @click=${()=>i(e+1)}>
          Next
        </button>
        <select
          @change=${t=>{const e=t.target.value;a("all"===e?"all":Number(e))}}
        >
          ${Zt.map(t=>B`<option value=${String(t)} ?selected=${t===s}>${"all"===t?"All":`${t} / page`}</option>`)}
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
      `:W}_renderProtectDevices(t){return t.length?B`
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>IP</th>
              <th>MAC</th>
              <th>Recording</th>
              <th>Last Ring</th>
              <th>Channels</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            ${t.map(t=>B`
                <tr>
                  <td>
                    <div style="font-weight:600;">
                      ${t.link?B`<a class="thumb-link" href=${t.link} target="_blank" rel="noopener"
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
                    ${t.link?B`<a class="thumb-link" href=${t.link} target="_blank" rel="noopener">Open ↗</a>`:W}
                  </td>
                </tr>
              `)}
          </tbody>
        </table>
      </div>
      <div class="note">
        Device names link to that camera on the Protect console
        (<code>https://&lt;host&gt;/protect/dashboard/devices/&lt;id&gt;</code>).
      </div>
    `:B`<div class="empty">No Protect devices reported.</div>`}_fmtDuration(t){if(null==t)return"—";if(t<60)return`${t}s`;const e=Math.floor(t/60);if(e<60)return`${e}m ${t%60}s`;return`${Math.floor(e/60)}h ${e%60}m`}_renderProtectEvents(t){return B`
      <div class="card">
        <h3>Events &amp; AI Smart Detections <span class="muted" style="font-weight:400;font-size:12px;">— last 24h</span></h3>
        ${t.events_error?B`<div class="note" style="font-size:13px;">${t.events_error}</div>`:t.events.length?B`
                <div class="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Type</th>
                        <th>Smart Detections</th>
                        <th class="num">Score</th>
                        <th>Start</th>
                        <th class="num">Duration</th>
                        <th>Thumbnail</th>
                        <th>License Plate</th>
                      </tr>
                    </thead>
                    <tbody>
                      ${t.events.map(t=>B`
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
                              ${t.thumbnail_link?B`<a class="thumb-link" href=${t.thumbnail_link} target="_blank" rel="noopener"
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
    `}};function Qt(t){const e=t.match(/^homeassistant\.components\.([^.]+)/);if(e)return e[1];const s=t.match(/^custom_components\.([^.]+)/);return s?s[1]:t.split(".")[0]}Jt.styles=[Ft,o`
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
    `],t([pt({attribute:!1})],Jt.prototype,"hass",void 0),t([ut()],Jt.prototype,"_overview",void 0),t([ut()],Jt.prototype,"_loading",void 0),t([ut()],Jt.prototype,"_error",void 0),t([ut()],Jt.prototype,"_clientSearch",void 0),t([ut()],Jt.prototype,"_clientPage",void 0),t([ut()],Jt.prototype,"_clientPageSize",void 0),t([ut()],Jt.prototype,"_clientVlanFilter",void 0),t([ut()],Jt.prototype,"_clientSsidFilter",void 0),t([ut()],Jt.prototype,"_deviceSearch",void 0),t([ut()],Jt.prototype,"_devicePage",void 0),t([ut()],Jt.prototype,"_devicePageSize",void 0),Jt=t([dt("ha-soc-network-view")],Jt);const Xt=["DEBUG","INFO","WARNING","ERROR","CRITICAL"];let te=class extends rt{constructor(){super(...arguments),this._entries=[],this._fault=null,this._loading=!0,this._domainFilter="",this._levelFilter="",this._expanded=new Set}connectedCallback(){super.connectedCallback(),this._load()}async _load(){this._loading=!0;try{const[e,s]=await Promise.all([(t=this.hass,vt(t,{type:"system_log/list"})),ft(this.hass)]);this._entries=e,this._fault=s}finally{this._loading=!1}var t}_toggleExpanded(t){const e=new Set(this._expanded);e.has(t)?e.delete(t):e.add(t),this._expanded=e}get _domains(){return Array.from(new Set(this._entries.map(t=>Qt(t.name)))).sort()}get _levels(){const t=new Set(this._entries.map(t=>t.level.toUpperCase()));return Xt.filter(e=>t.has(e))}get _filtered(){return this._entries.filter(t=>(!this._domainFilter||Qt(t.name)===this._domainFilter)&&(!this._levelFilter||t.level.toUpperCase()===this._levelFilter))}_renderFaultLogCard(){const t=this._fault;return t?B`
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
    `:W}render(){const t=this._filtered;return B`
      ${this._renderFaultLogCard()}

      <div class="card">
        <h3>Home Assistant Logs</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          The same WARNING/ERROR/CRITICAL buffer as Settings → System → Logs
          (<code>/config/logs</code>) — deduplicated, most recent first. This shows Home
          Assistant's own captured log records only;
          <strong>add-on container logs aren't included</strong> — they're a separate
          stream Supervisor captures per-container, not part of Home Assistant's Python
          logging, so there's nothing for this view to filter. Check an add-on's own
          Log tab (Settings → Add-ons → the add-on → Log) for those.
        </p>
        <div class="toolbar">
          <select @change=${t=>this._domainFilter=t.target.value}>
            <option value="" ?selected=${""===this._domainFilter}>All integrations</option>
            ${this._domains.map(t=>B`<option value=${t} ?selected=${t===this._domainFilter}>${t}</option>`)}
          </select>
          <select @change=${t=>this._levelFilter=t.target.value}>
            <option value="" ?selected=${""===this._levelFilter}>All levels</option>
            ${this._levels.map(t=>B`<option value=${t} ?selected=${t===this._levelFilter}>${t}</option>`)}
          </select>
          <span class="spacer"></span>
          <button class="ha-btn" @click=${this._load}>Refresh</button>
        </div>
        ${this._loading?B`<div class="empty">Loading…</div>`:t.length?B`
              <table>
                <thead>
                  <tr>
                    <th>Time</th>
                    <th>Level</th>
                    <th>Integration</th>
                    <th>Message</th>
                    <th>Count</th>
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
                          <span class="log-level ${function(t){const e=t.toUpperCase();return Xt.includes(e)?e.toLowerCase():"info"}(t.level)}"
                            ><span class="dot"></span>${t.level}</span
                          >
                        </td>
                        <td class="muted">${Qt(t.name)}</td>
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
            `:B`<div class="empty">No matching log entries.</div>`}
      </div>
    `}};te.styles=[Ft,o`
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
      .fault-log pre {
        white-space: pre-wrap;
        font-size: 11.5px;
        background: rgba(var(--rgb-primary-text-color, 0, 0, 0), 0.04);
        padding: 10px;
        border-radius: 6px;
        margin: 0;
        max-height: 400px;
        overflow-y: auto;
      }
    `],t([pt({attribute:!1})],te.prototype,"hass",void 0),t([ut()],te.prototype,"_entries",void 0),t([ut()],te.prototype,"_fault",void 0),t([ut()],te.prototype,"_loading",void 0),t([ut()],te.prototype,"_domainFilter",void 0),t([ut()],te.prototype,"_levelFilter",void 0),t([ut()],te.prototype,"_expanded",void 0),te=t([dt("ha-soc-logs-view")],te);let ee=class extends rt{constructor(){super(...arguments),this._overview=null,this._loading=!0,this._busyKey=null,this._showIgnored=!1}connectedCallback(){super.connectedCallback(),this._load()}async _load(){this._loading=!0;try{this._overview=await At(this.hass)}finally{this._loading=!1}}async _onToggleIgnore(t,e,s){this._busyKey=t;try{await((t,e,s,i)=>vt(t,{type:"ha_soc/peripherals/set_ignored",key:e,ignored:s,raw_name:i}))(this.hass,t,e,s),await this._load()}finally{this._busyKey=null}}render(){if(this._loading)return B`<div class="empty">Loading peripherals…</div>`;const t=this._overview;if(!t||!t.available)return B`
        <div class="card">
          <h3>Local Peripherals</h3>
          <p class="muted" style="font-size:12.5px;">
            Home Assistant's own USB discovery component (<code>usb</code>) isn't
            available — it's part of every default install, so this usually only
            happens if it's been explicitly disabled. This view has nothing to read
            without it.
          </p>
        </div>
      `;const e=t.devices.filter(t=>!t.ignored),s=t.devices.filter(t=>t.ignored);return B`
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
                    <th>Raw Name</th>
                    <th>/dev/tty Path</th>
                    <th>Assigned Integration</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  ${e.map(t=>B`
                      <tr>
                        <td>${t.raw_name}</td>
                        <td class="muted">${t.tty_path}</td>
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

      ${s.length?B`
            <div class="card">
              <h3 style="cursor:pointer;" @click=${()=>this._showIgnored=!this._showIgnored}>
                Ignored (${s.length}) ${this._showIgnored?"▲":"▼"}
              </h3>
              ${this._showIgnored?B`
                    <table>
                      <thead>
                        <tr>
                          <th>Raw Name</th>
                          <th>/dev/tty Path</th>
                          <th></th>
                        </tr>
                      </thead>
                      <tbody>
                        ${s.map(t=>B`
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
          `:W}
    `}};ee.styles=Ft,t([pt({attribute:!1})],ee.prototype,"hass",void 0),t([ut()],ee.prototype,"_overview",void 0),t([ut()],ee.prototype,"_loading",void 0),t([ut()],ee.prototype,"_busyKey",void 0),t([ut()],ee.prototype,"_showIgnored",void 0),ee=t([dt("ha-soc-peripherals-view")],ee);const se={automation:"Automations",script:"Scripts",scene:"Scenes",dashboard:"Views (dashboards)",helper:"Helpers",other:"Other (review manually)"};let ie=class extends rt{constructor(){super(...arguments),this._entities=[],this._oldEntityId="",this._newEntityId="",this._report=null,this._finding=!1,this._applying=!1,this._applyResult=null,this._broken=[],this._brokenLoading=!0,this._brokenFilter=null,this._filterSameType=!0}connectedCallback(){super.connectedCallback(),this._load()}async _load(){const[t,e]=await Promise.all([(s=this.hass,vt(s,{type:"config/entity_registry/list"})),Ct(this.hass)]);var s;this._entities=t,this._broken=e,this._brokenLoading=!1}_labelFor(t){const e=this._entities.find(e=>e.entity_id===t),s=e?.name||e?.original_name;return s?`${s} (${t})`:t}async _onFind(){if(this._oldEntityId){this._finding=!0,this._applyResult=null;try{this._report=await(t=this.hass,e=this._oldEntityId,vt(t,{type:"ha_soc/entity_remap/find_references",entity_id:e})),this._brokenFilter=this._oldEntityId}finally{this._finding=!1}var t,e}}_onFixBroken(t){this._oldEntityId=t,this._newEntityId="",this._report=null,this._applyResult=null,this._onFind()}_selectOld(t){this._oldEntityId=t,this._newEntityId="",this._report=null,this._applyResult=null,this.updateComplete.then(()=>{this.renderRoot?.querySelector("#remap-card")?.scrollIntoView({behavior:"smooth",block:"start"})})}_domainOf(t){return t.includes(".")?t.split(".",1)[0]:""}_newEntityOptions(){const t=this._domainOf(this._oldEntityId);return this._filterSameType&&t?this._entities.filter(e=>this._domainOf(e.entity_id)===t):this._entities}_onClearBrokenFilter(){this._brokenFilter=null}_filteredBroken(){return this._brokenFilter?this._broken.filter(t=>t.entity_id===this._brokenFilter):this._broken}async _onApply(){if(this._oldEntityId&&this._newEntityId){this._applying=!0;try{const i=await(t=this.hass,e=this._oldEntityId,s=this._newEntityId,vt(t,{type:"ha_soc/entity_remap/apply",old_entity_id:e,new_entity_id:s}));await this._onFind(),this._broken=await Ct(this.hass),this._applyResult=i}finally{this._applying=!1}var t,e,s}}_renderKind(t,e){return e.length?B`
      <div style="margin-bottom:12px;">
        <div style="font-size:12px;font-weight:600;color:var(--secondary-text-color);margin-bottom:4px;">
          ${se[t]??t} (${e.length})
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
    `:W}render(){const t=this._report,e=!!t&&t.editable_count>0&&!!this._newEntityId&&this._newEntityId!==this._oldEntityId;return B`
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
                <button class="ha-btn" ?disabled=${!e||this._applying} @click=${()=>this._onApply()}>
                  ${this._applying?"Applying…":`Apply remap (${t.editable_count} reference${1===t.editable_count?"":"s"})`}
                </button>
              </div>
            `:W}

        ${this._applyResult?B`
              <div class="card" style="margin-top:12px;background:rgba(67,160,71,0.08);">
                <strong>Applied.</strong> ${Object.entries(this._applyResult.fixed).filter(([,t])=>t>0).map(([t,e])=>`${e} ${se[t]??t}`).join(", ")||"Nothing needed changing."}
                ${this._applyResult.errors.length?B`<div style="color:var(--error-color);margin-top:6px;">
                      ${this._applyResult.errors.length} error(s): ${this._applyResult.errors.join("; ")}
                    </div>`:W}
              </div>
            `:W}
      </div>

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
        ${this._brokenLoading?B`<div class="empty">Loading…</div>`:this._broken.length?this._filteredBroken().length?B`
                <table>
                  <thead>
                    <tr>
                      <th>Entity ID</th>
                      <th>Referenced by</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    ${this._filteredBroken().map(t=>B`
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
    `}};ie.styles=Ft,t([pt({attribute:!1})],ie.prototype,"hass",void 0),t([ut()],ie.prototype,"_entities",void 0),t([ut()],ie.prototype,"_oldEntityId",void 0),t([ut()],ie.prototype,"_newEntityId",void 0),t([ut()],ie.prototype,"_report",void 0),t([ut()],ie.prototype,"_finding",void 0),t([ut()],ie.prototype,"_applying",void 0),t([ut()],ie.prototype,"_applyResult",void 0),t([ut()],ie.prototype,"_broken",void 0),t([ut()],ie.prototype,"_brokenLoading",void 0),t([ut()],ie.prototype,"_brokenFilter",void 0),t([ut()],ie.prototype,"_filterSameType",void 0),ie=t([dt("ha-soc-entity-remap-view")],ie);const ae={core:"Core",hacs:"HACS",custom:"Custom"},ne={core:"good",hacs:"medium",custom:"high"},oe={custom_repo:"Custom repo",custom_source_list:"Custom source-list"};let re=class extends rt{constructor(){super(...arguments),this._overview=null,this._loading=!0,this._refreshing=!1,this._search="",this._tierFilter="all",this._limit=25}connectedCallback(){super.connectedCallback(),this._load()}async _load(){this._loading=!0;try{this._overview=await(t=this.hass,vt(t,{type:"ha_soc/integration_security/list"}))}finally{this._loading=!1}var t}async _onRefresh(){this._refreshing=!0;try{await(t=this.hass,vt(t,{type:"ha_soc/integration_security/refresh"})),await this._load()}finally{this._refreshing=!1}var t}_filtered(){const t=this._overview?.integrations??[],e=this._search.trim().toLowerCase();return t.filter(t=>"all"===this._tierFilter||t.tier===this._tierFilter).filter(t=>!e||t.name.toLowerCase().includes(e)||t.domain.toLowerCase().includes(e)).sort((t,e)=>t.name.localeCompare(e.name))}render(){if(this._loading||!this._overview)return B`<div class="empty">Loading integrations…</div>`;const t=this._overview,e=this._filtered(),s=e.slice(0,this._limit);return B`
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
                      <th>Integration</th>
                      <th>Source</th>
                      <th>Quality</th>
                      <th>License</th>
                      <th>Scanner</th>
                      <th>Signed</th>
                      <th>Release</th>
                      <th>Stars</th>
                      <th>Last push</th>
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
    `}_notCollected(){return B`<span class="muted" title="No GitHub token, or no repo URL discovered">—</span>`}_renderRow(t){const e=t.github;return B`
      <tr>
        <td>
          <div style="font-weight:600;">${t.name}</div>
          <div class="muted" style="font-size:11.5px;">
            ${t.domain}${t.version?B` · v${t.version}`:""}
          </div>
          ${t.flags.length?B`<div class="chips" style="margin-top:3px;">
                ${t.flags.map(t=>B`<span class="pill high"><span class="dot"></span>${oe[t]??t}</span>`)}
              </div>`:W}
        </td>
        <td>
          <span class="pill ${ne[t.tier]}"><span class="dot"></span>${ae[t.tier]}</span>
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
    `}};re.styles=Ft,t([pt({attribute:!1})],re.prototype,"hass",void 0),t([ut()],re.prototype,"_overview",void 0),t([ut()],re.prototype,"_loading",void 0),t([ut()],re.prototype,"_refreshing",void 0),t([ut()],re.prototype,"_search",void 0),t([ut()],re.prototype,"_tierFilter",void 0),t([ut()],re.prototype,"_limit",void 0),re=t([dt("ha-soc-integration-security-view")],re);const le=1048576,de=[{domain:"lock",label:"Lock entities (any integration)"},{domain:"siren",label:"Siren entities (any integration)"},{domain:"valve",label:"Valve entities (any integration)"}],ce=[{domain:"kidde_homesafe",label:"Kidde HomeSafe"},{domain:"elkm1",label:"Elk-M1 Security"},{domain:"unifiprotect",label:"UniFi Protect"},{domain:"keymaster",label:"Keymaster"},{domain:"emporia_vue",label:"Emporia Vue"}];let he=class extends rt{constructor(){super(...arguments),this._settings=null,this._security=null,this._loading=!0}connectedCallback(){super.connectedCallback(),this._load()}async _load(){this._loading=!0;try{this._settings=await(t=this.hass,vt(t,{type:"ha_soc/settings/get"}));try{this._security=await Pt(this.hass)}catch{this._security=null}}finally{this._loading=!1}var t}async _update(t,e){if(!this._settings)return;const s=this._settings;this._settings={...this._settings,[t]:e};try{this._settings=await(i=this.hass,a={[t]:e},vt(i,{type:"ha_soc/settings/set",...a}))}catch(t){throw this._settings=s,t}var i,a}_updateSecuritySource(t,e){this._settings&&this._update("security_sources_enabled",{...this._settings.security_sources_enabled,[t]:e})}_renderSecretField(t,e,s){return B`
      <label class="settings-row">
        <span>${t}</span>
        <input
          type="password"
          placeholder=${s?"configured — type to replace":"unset"}
          @change=${t=>{const s=t.target.value;this._update(e,s||null)}}
        />
      </label>
    `}_renderIntegrationRow(t,e){const s=this._settings,i=this._security?.integrations.filter(e=>e.domain===t)??[],a=i.some(t=>t.installed),n=i.some(t=>t.installed&&"loaded"!==t.state),o=i.find(t=>t.installed)?.entry_id??null,r=a?n?i.find(t=>"loaded"!==t.state).state:"loaded":"not installed";return B`
      <div class="settings-row">
        <span>${e}</span>
        <span
          class="muted ${a&&o?"clickable":""}"
          style="font-size:12px;${n?"color:var(--error-color,#db4437);":""}"
          title=${a&&o?"View in Home Assistant's Devices page":""}
          @click=${()=>a&&o&&Tt(Mt(o))}
          >${r}</span
        >
        <input
          type="checkbox"
          .checked=${s.security_sources_enabled?.[t]??!0}
          @change=${e=>this._updateSecuritySource(t,e.target.checked)}
        />
      </div>
    `}render(){if(this._loading||!this._settings)return B`<div class="empty">Loading settings…</div>`;const t=this._settings;return B`
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
        ${this._renderSecretField("NVD API key (optional — raises the public rate limit)","nvd_api_key",!!t.nvd_api_key_set)}
        <label class="settings-row">
          <span>Risk-scoring learning period (days)</span>
          <input
            type="number"
            min="1"
            max="90"
            .value=${String(t.risk_learning_period_days)}
            @change=${t=>this._update("risk_learning_period_days",Number(t.target.value))}
          />
        </label>
      </div>

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
            .value=${String(Math.round(t.audit_max_bytes/le))}
            @change=${t=>this._update("audit_max_bytes",Math.round(Number(t.target.value)*le))}
          />
        </label>
      </div>

      <div class="card">
        <h3>Security Integrations Health</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          What shows up in the always-present Dashboard security card. A source stays on
          by default — a device or integration you haven't installed just reports "not
          installed" rather than being hidden, and turning a toggle off here only affects
          this dashboard section, nothing else.
        </p>
        ${de.map(({domain:e,label:s})=>B`
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
        ${ce.map(({domain:t,label:e})=>this._renderIntegrationRow(t,e))}
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
    `}};he.styles=Ft,t([pt({attribute:!1})],he.prototype,"hass",void 0),t([ut()],he.prototype,"_settings",void 0),t([ut()],he.prototype,"_security",void 0),t([ut()],he.prototype,"_loading",void 0),he=t([dt("ha-soc-settings-view")],he);const pe=[{id:"dashboard",label:"Dashboard"},{id:"network",label:"Network"},{id:"entity_remap",label:"Entity ReMap"},{id:"integration_security",label:"Integration Security"},{id:"users",label:"Users & Access"},{id:"permissions",label:"Permissions"},{id:"audit",label:"Audit Log"},{id:"peripherals",label:"Local Peripherals"},{id:"scanner",label:"Scanner"},{id:"logs",label:"Logs"},{id:"settings",label:"Settings",ownerOnly:!0}];let ue=class extends rt{constructor(){super(...arguments),this._tab="dashboard",this._access=null,this._version=null,this._probe=null}connectedCallback(){super.connectedCallback(),this._loadAccess(),this._loadFooterInfo()}async _loadAccess(){try{this._access=await(t=this.hass,vt(t,{type:"ha_soc/access/info"}))}catch{this._access={is_owner:!1,access_level:"owner_only",allowed:!1}}var t}async _loadFooterInfo(){try{this._version=(await(t=this.hass,vt(t,{type:"ha_soc/version/get"}))).version}catch{this._version=null}var t;try{this._probe=await kt(this.hass)}catch{this._probe=null}}_renderFooter(){if(!this._version)return B``;const t=this._probe?.installed&&this._probe.version?` · HA SOC Probe v${this._probe.version}`:"";return B`<div class="footer">HA SOC v${this._version}${t}</div>`}render(){return null===this._access?B`<div class="header">🛡️ HA SOC</div>`:this._access.allowed?B`
      <div class="header">🛡️ HA SOC</div>
      <div class="tabs">
        ${pe.map(t=>!!t.ownerOnly&&!this._access?.is_owner?B`
              <div class="tab disabled" title="Only available to the account owner">
                ${t.label}<span class="lock">🔒</span>
              </div>
            `:B`
            <div class="tab ${this._tab===t.id?"active":""}" @click=${()=>this._tab=t.id}>
              ${t.label}
            </div>
          `)}
      </div>
      <div @ha-soc-navigate=${this._onNavigate}>${this._renderTab()}</div>
      ${this._renderFooter()}
    `:B`
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
      `}_onNavigate(t){this._tab=t.detail.tab}_renderTab(){switch(this._tab){case"users":return B`<ha-soc-users-view .hass=${this.hass}></ha-soc-users-view>`;case"audit":return B`<ha-soc-audit-view .hass=${this.hass}></ha-soc-audit-view>`;case"permissions":return B`<ha-soc-permissions-view .hass=${this.hass}></ha-soc-permissions-view>`;case"scanner":return B`<ha-soc-scanner-view .hass=${this.hass}></ha-soc-scanner-view>`;case"logs":return B`<ha-soc-logs-view .hass=${this.hass}></ha-soc-logs-view>`;case"peripherals":return B`<ha-soc-peripherals-view .hass=${this.hass}></ha-soc-peripherals-view>`;case"network":return B`<ha-soc-network-view .hass=${this.hass}></ha-soc-network-view>`;case"entity_remap":return B`<ha-soc-entity-remap-view .hass=${this.hass}></ha-soc-entity-remap-view>`;case"integration_security":return B`<ha-soc-integration-security-view .hass=${this.hass}></ha-soc-integration-security-view>`;case"settings":return this._access?.is_owner?B`<ha-soc-settings-view .hass=${this.hass}></ha-soc-settings-view>`:B`<div class="denied"><div class="icon">🔒</div><h2>Owner only</h2>
            <p>The Settings tab is available to the account owner only.</p></div>`;default:return B`<ha-soc-dashboard-view .hass=${this.hass}></ha-soc-dashboard-view>`}}};ue.styles=o`
    :host {
      display: block;
      background: var(--primary-background-color);
      min-height: 100vh;
    }
    .tabs {
      display: flex;
      gap: 4px;
      border-bottom: 1px solid var(--divider-color);
      padding: 0 16px;
      background: var(--card-background-color, #fff);
      overflow-x: auto;
    }
    .tab {
      padding: 14px 16px;
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
      gap: 8px;
      padding: 12px 16px 0;
      font-size: 20px;
      font-weight: 500;
      color: var(--primary-text-color);
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
  `,t([pt({attribute:!1})],ue.prototype,"hass",void 0),t([pt({attribute:!1})],ue.prototype,"narrow",void 0),t([pt({attribute:!1})],ue.prototype,"panel",void 0),t([ut()],ue.prototype,"_tab",void 0),t([ut()],ue.prototype,"_access",void 0),t([ut()],ue.prototype,"_version",void 0),t([ut()],ue.prototype,"_probe",void 0),ue=t([dt("ha-soc-panel")],ue);export{ue as HaSocPanel};
