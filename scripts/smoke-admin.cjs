// Run against the freshly seeded local SUT and its Admin Vite server.
const { chromium } = require("playwright");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const out = path.resolve(process.argv[2]);
const base = "http://127.0.0.1:3000/api";
const checks = [];
async function main() {
  const browser = await chromium.launch({channel:"chrome", headless:true});
  try {
    const page = await browser.newPage({viewport:{width:1250,height:800}});
    await page.goto("http://127.0.0.1:5174");
    await page.getByPlaceholder("Email").fill("g4-1@example.test");
    await page.getByPlaceholder("Password").fill("LocalDemo123!");
    await page.getByRole("button", {name:"Login"}).click();
    await page.getByRole("heading", {name:"Dashboard"}).waitFor();
    const orderCount = page.getByRole("heading",{name:"Tổng số đơn hàng"}).locator("..").locator("p");
    await page.waitForFunction(() => [...document.querySelectorAll("h3")].some(h => h.textContent==="Tổng số đơn hàng" && h.nextElementSibling?.textContent==="1"));
    assert.equal(await orderCount.textContent(),"1");
    const revenue = page.getByRole("heading",{name:"Tổng doanh thu (Delivered)"}).locator("..").locator("p");
    assert.equal((await revenue.textContent()).trim(),"0 ₫");
    await page.screenshot({path:path.join(out,"dashboard.png")});
    checks.push(["FR-12/13","Admin login, Dashboard", "1 order; 0 delivered revenue"]);
    const token = await page.evaluate(()=>localStorage.getItem("adminToken"));
    assert.ok(token);
    async function api(method, uri, data) {
      const resp = await page.request.fetch(base+uri,{method, data, headers:{Authorization:"Bearer "+token}});
      assert.equal(resp.status(),200,method+" "+uri);
      return resp.json();
    }
    const orders = await api("GET","/admin/orders");
    assert(orders.some(o=>o.id===9001 && o.status==="pending"));
    assert((await api("GET","/admin/users")).some(u=>u.email==="g4-1@example.test" && u.role==="admin"));
    checks.push(["FR-18/19","Order and user lists","Order 9001 pending; demo admin present"]);
    const category = await api("POST","/categories",{name:"G4-Smoke"});
    assert((await api("GET","/categories")).some(c=>c.id===category.id && c.name==="G4-Smoke"));
    await api("PUT","/categories/"+category.id,{name:"G4-Smoke-Edited"});
    assert((await api("GET","/categories")).some(c=>c.id===category.id && c.name==="G4-Smoke-Edited"));
    const form = {name:"G4-Smoke",price:100001,description:"Smoke",imageUrl:"",category_id:category.id};
    const product = await api("POST","/products",form);
    const uri = "/products/"+product.id;
    assert.equal(Number((await api("GET",uri)).price),100001);
    await api("PUT",uri,{...form,price:101001});
    assert.equal(Number((await api("GET",uri)).price),101001);
    await api("DELETE",uri);
    assert(!(await api("GET","/products")).some(p=>p.id===product.id));
    await api("DELETE","/categories/"+category.id);
    assert(!(await api("GET","/categories")).some(c=>c.id===category.id));
    checks.push(["FR-14/15","Create, read, update, reread, delete","Removed owned category "+category.id+" and product "+product.id]);
    const coupon = await api("POST","/admin/coupons",{code:"G4SMOKE",type:"percent",discount_value:10,min_order_amount:0,expired_at:"2099-12-31",max_uses_per_user:1});
    assert((await api("GET","/coupons")).some(c=>c.id===coupon.id && c.code==="G4SMOKE"));
    await api("DELETE","/admin/coupons/"+coupon.id);
    assert(!(await api("GET","/coupons")).some(c=>c.id===coupon.id));
    checks.push(["FR-17","Create, read, delete coupon","G4SMOKE absent after deletion"]);
    await page.getByText("Sản phẩm",{exact:true}).first().click();
    await page.locator('input[type=file]').setInputFiles(path.resolve("data/import-products.csv"));
    await page.getByText("Xem trước (2 dòng):",{exact:true}).waitFor();
    await page.screenshot({path:path.join(out,"csv-preview.png")});
    const response = page.waitForResponse(r=>r.url().endsWith("/admin/import-products") && r.request().method()==="POST");
    await page.getByRole("button",{name:"Import 2 sản phẩm"}).click();
    const result = await (await response).json();
    await page.getByText(/Import hoàn tất:/).waitFor();
    await page.screenshot({path:path.join(out,"csv-result.png")});
    assert.equal(result.inserted,2);
    const products = await api("GET","/products");
    for (const [name,price] of [["G4-import-A",120000],["G4-import-B",135000]]) {
      assert(products.some(p=>p.name===name && Number(p.price)===price));
    }
    checks.push(["FR-16","CSV via UI, two rows; persisted values checked",result.message]);
  } finally {
    fs.writeFileSync(path.join(out,"checks.json"),JSON.stringify(checks,null,2));
    await browser.close();
  }
}
main().catch(e=>{console.error(e);process.exitCode=1});
