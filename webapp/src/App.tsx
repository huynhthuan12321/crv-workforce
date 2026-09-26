import {useEffect, useState} from "react";
import {api, ApiError} from "./api/client";
import {useTelegram} from "./hooks/useTelegram";
import "./styles/globals.css";
import "./styles/telegram-theme.css";

type Employee = {id:number; code:string; full_name:string; role:"employee"|"manager"|"director"; tabs:string[]};
type Session = {id:number; check_in_at:string; check_out_at?:string; minutes?:number; flags:string[]};

const money=(n:number)=>new Intl.NumberFormat("vi-VN").format(n)+"đ";

function Attendance(){
  const [status,setStatus]=useState<any>(); const [error,setError]=useState("");
  const load=()=>api.get<any>("/attendance/today").then(setStatus).catch(e=>setError(e.message));
  useEffect(()=>{void load()},[]);
  const action=(kind:"check-in"|"check-out")=>navigator.geolocation.getCurrentPosition(async p=>{
    try {await api.post(`/attendance/${kind}`,{lat:p.coords.latitude,lng:p.coords.longitude,accuracy_m:p.coords.accuracy}); setError(""); load();}
    catch(e){setError((e as Error).message)}
  },()=>setError("Vui lòng bật quyền vị trí để chấm công."),{enableHighAccuracy:true});
  if(!status)return <Card>Đang tải...</Card>;
  return <><Card><h2>{status.open_session?"Đang trong ca":"Chưa vào ca"}</h2>
    {status.open_session&&<p>Vào lúc {new Date(status.open_session.check_in_at).toLocaleTimeString("vi-VN",{hour:"2-digit",minute:"2-digit"})}</p>}
    <p className="amount">{money(status.estimated_day_amount)}</p><small>Lương tạm tính hôm nay</small>
    <button className={status.open_session?"danger":"primary"} onClick={()=>action(status.open_session?"check-out":"check-in")}>{status.open_session?"RA CA":"VÀO CA"}</button>
    {error&&<p className="error">{error}</p>}</Card></>;
}

function Outputs(){const [id,setId]=useState("");const [form,setForm]=useState<any>();const [error,setError]=useState("");
 const load=()=>api.get<any>(`/outputs/${id}`).then(setForm).catch(e=>setError(e.message));
 const save=()=>api.put(`/outputs/${id}`,{items:Object.fromEntries(form.items.map((x:any)=>[x.code,x.bags]))}).then(load).catch(e=>setError((e as Error).message));
 return <Card><h2>Sản lượng</h2><input placeholder="Mã phiên vừa ra ca" value={id} onChange={e=>setId(e.target.value)}/><button className="secondary" onClick={load}>Mở bản khai</button>{form&&<>{form.items.map((x:any)=><label className="row" key={x.code}><span>{x.name}<small>{x.kg_per_bag} kg/túi</small></span><input type="number" min="0" disabled={form.locked} value={x.bags} onChange={e=>setForm({...form,items:form.items.map((i:any)=>i.code===x.code?{...i,bags:+e.target.value}:i)})}/></label>)}<p>Còn {Math.floor(form.seconds_remaining/60)}:{String(form.seconds_remaining%60).padStart(2,"0")}</p><button className="primary" disabled={form.locked} onClick={save}>Lưu sản lượng</button></>}{error&&<p className="error">{error}</p>}</Card>}

function History(){const [data,setData]=useState<any>();useEffect(()=>{api.get<any>("/history").then(setData)},[]);return <Card><h2>Lịch sử</h2>{!data?"Đang tải...":data.sessions.map((x:Session)=><div className="list" key={x.id}><b>{new Date(x.check_in_at).toLocaleDateString("vi-VN")}</b><span>{new Date(x.check_in_at).toLocaleTimeString("vi-VN",{hour:"2-digit",minute:"2-digit"})} – {x.check_out_at?new Date(x.check_out_at).toLocaleTimeString("vi-VN",{hour:"2-digit",minute:"2-digit"}):"Chưa ra"}</span></div>)}</Card>}

function Review(){const [rows,setRows]=useState<any[]>([]);const load=()=>api.get<any[]>("/review/pending").then(setRows);useEffect(()=>{void load()},[]);return <Card><h2>Cần xử lý</h2>{rows.length===0?<p>Không có mục cần xử lý</p>:rows.map(x=><div className="list" key={x.id}><b>Phiên #{x.id}</b><span>{x.status} · {x.flags.join(", ")}</span>{x.flags.length>0&&<button className="secondary" onClick={()=>api.post(`/review/${x.id}/flags-reviewed`).then(load)}>Đã xem</button>}</div>)}</Card>}

function Payroll(){const [date,setDate]=useState(new Date().toISOString().slice(0,10));const [rows,setRows]=useState<any[]>([]);return <Card><h2>Duyệt lương</h2><input type="date" value={date} onChange={e=>setDate(e.target.value)}/><button className="secondary" onClick={()=>api.get<any[]>(`/payroll?date=${date}`).then(setRows)}>Tải danh sách</button>{rows.map(x=><div className="list" key={x.employee_id}><b>{x.full_name}</b><span>{x.minutes} phút</span><button className="primary small" onClick={()=>api.post("/payroll/approve",{date,employee_ids:[x.employee_id]})}>Duyệt</button></div>)}</Card>}

function Employees(){const [rows,setRows]=useState<any[]>([]);useEffect(()=>{api.get<any[]>("/employees").then(setRows)},[]);return <Card><h2>Nhân viên</h2>{rows.map(x=><div className="list" key={x.id}><b>{x.full_name}</b><span>{x.code} · {x.is_active?"Đang hoạt động":"Đã khóa"}</span></div>)}</Card>}
function Reports(){const [data,setData]=useState<any>();const today=new Date().toISOString().slice(0,10);useEffect(()=>{api.get<any>(`/reports/summary?period=day&date=${today}`).then(setData)},[]);return <Card><h2>Báo cáo hôm nay</h2>{data&&<div className="stats"><b>{data.minutes} phút</b><b>{money(data.salary)}</b><b>{data.bags} túi</b><b>{data.kg} kg</b></div>}</Card>}
function Card({children}:{children:any}){return <section className="card">{children}</section>}

export default function App(){useTelegram();const [user,setUser]=useState<Employee>();const [tab,setTab]=useState("");const [error,setError]=useState("");
 useEffect(()=>{window.Telegram?.WebApp?.ready();window.Telegram?.WebApp?.expand();api.login().then(x=>{setUser(x.employee);setTab(x.employee.tabs[0])}).catch((e:ApiError)=>setError(e.message))},[]);
 if(error)return <main><Card><h2>Không thể mở ứng dụng</h2><p className="error">{error}</p></Card></main>;
 if(!user)return <main><Card>Đang xác thực với Telegram...</Card></main>;
 const views:any={attendance:<Attendance/>,outputs:<Outputs/>,history:<History/>,working:<Card><h2>Đang làm</h2><p>Danh sách được cập nhật từ máy chủ.</p></Card>,review:<Review/>,payroll:<Payroll/>,employees:<Employees/>,reports:<Reports/>};
 const labels:any={attendance:"Chấm công",outputs:"Sản lượng",history:"Lịch sử",working:"Đang làm",review:"Cần xử lý",payroll:"Duyệt lương",employees:"Nhân viên",reports:"Báo cáo"};
 return <main><header><div><small>CRV WORKFORCE</small><h1>{user.full_name}</h1></div><span className="badge">{user.code}</span></header>{views[tab]}<nav>{user.tabs.map(x=><button className={tab===x?"active":""} key={x} onClick={()=>setTab(x)}>{labels[x]}</button>)}</nav></main>}
