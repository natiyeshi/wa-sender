c =
d = []
for(i in c){
    if(c[i].reason == "open_chat_failed"){
        d.push(c[i])
    }
}

console.log(d.length, c.length)

