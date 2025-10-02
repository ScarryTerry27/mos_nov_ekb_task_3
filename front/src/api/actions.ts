import {withPublicAPIToken} from '@/api/api';
import {LoginRequest} from "@/dto/auth.dto";

export const login = async (data: LoginRequest) =>
  await withPublicAPIToken({
    url: `/auth/login`,
    method: 'post',
    data: {...data},
  });

export const getObjects = async (params: { offset: number; limit: number; user_id: number }) =>
  withPublicAPIToken({
    url: '/objects/',             // заметь: с хвостовым слэшем, как в твоём curl
    method: 'get',
    params,                       // вот так axios добавит ?user_id=...&limit=...&offset=...
  });

export const getObject = async (queryString: any) =>
  await withPublicAPIToken({
    url: `/objects/${queryString}`,
    method: 'get',
  })

export const patchObject = async ({objectId, ...data}: any) =>
  await withPublicAPIToken({
    url: `/objects/${objectId}`,
    method: 'patch',
    data: {...data},
  })

export const getSubObjects = async (params : {offset : number; limit: number; object_id: number}) =>
  await withPublicAPIToken({
    url: `/subobjects/`,
    method: 'get',
    params,
  })

export const getSubObject = async (queryString: any) =>
  await withPublicAPIToken({
    url: `/subobjects/${queryString}`,
    method: 'get',
  })

export const patchSubObject = async ({subObjectId, ...data}: any) =>
  await withPublicAPIToken({
    url: `/subobjects/${subObjectId}`,
    method: 'patch',
    data: {...data},
  })

export const uploadVideo = async (formData: FormData) => {
  return await withPublicAPIToken({
    url: `/checks/process-video?role=inspector`,
    method: "post",
    data: formData,
    headers: {
      'Content-Type': 'multipart/form-data',
    }
  });
};

export const putCheck = async (data: any) => {
  return await withPublicAPIToken({
    url: `/checks/${data.check_id}`,
    method: 'put',
    data: data,
  })
}

export const putIncident = async (data: any) => {
  return await withPublicAPIToken({
    url: `/incidents/${data.incident_id}`,
    method: 'put',
    data: data,
  })
}



